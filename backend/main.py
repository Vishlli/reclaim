from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db, Base, engine
from models import Transaction, Policy, ManualReview, RecoveryEvent
from schemas import (
    TransactionOut, PolicyOut, PolicyUpdate, ManualReviewOut,
    AuditEventOut, DashboardOut, AnalyzeResponse, ExecuteResponse,
)
from services import transaction_service, recovery_service
import seed as seed_module

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RECLAIM — Revenue Recovery Control Plane")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_txn_or_404(db: Session, transaction_id: str) -> Transaction:
    txn = transaction_service.get_transaction_by_ref(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found.")
    return txn


@app.get("/")
def root():
    return {
        "product": "RECLAIM — Revenue Recovery Control Plane",
        "environment": "SIMULATED_TEST",
        "status": "ok",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    return transaction_service.compute_dashboard_metrics(db)


@app.get("/transactions", response_model=list[TransactionOut])
def get_transactions(db: Session = Depends(get_db)):
    return transaction_service.list_transactions(db)


@app.get("/transactions/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    return _get_txn_or_404(db, transaction_id)


@app.get("/recovery/cases", response_model=list[TransactionOut])
def recovery_cases(db: Session = Depends(get_db)):
    all_txns = transaction_service.list_transactions(db)
    return [
        t for t in all_txns
        if t.status in ("FAILED", "ABANDONED") or t.recovery_status == "MANUAL_REVIEW"
    ]


@app.get("/recovery/cases/{transaction_id}", response_model=TransactionOut)
def recovery_case_detail(transaction_id: str, db: Session = Depends(get_db)):
    return _get_txn_or_404(db, transaction_id)


@app.post("/recovery/analyze/{transaction_id}", response_model=AnalyzeResponse)
def analyze(transaction_id: str, db: Session = Depends(get_db)):
    txn = _get_txn_or_404(db, transaction_id)
    return recovery_service.analyze_transaction(db, txn)


@app.post("/recovery/execute/{transaction_id}", response_model=ExecuteResponse)
def execute(transaction_id: str, db: Session = Depends(get_db)):
    txn = _get_txn_or_404(db, transaction_id)
    result = recovery_service.execute_transaction(db, txn)
    return result


@app.get("/reviews", response_model=list[ManualReviewOut])
def get_reviews(db: Session = Depends(get_db)):
    return db.query(ManualReview).order_by(ManualReview.id.desc()).all()


@app.post("/reviews/{review_id}/approve")
def approve_review(review_id: int, db: Session = Depends(get_db)):
    review = db.query(ManualReview).filter(ManualReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    txn = db.query(Transaction).filter(Transaction.id == review.transaction_id).first()
    review.status = "APPROVED"
    review.reviewed_by = "merchant"
    review.reviewed_at = datetime.utcnow()
    db.commit()

    action = review.recommendation or "GENERATE_PAYMENT_LINK"
    from engine import executor, reconciliation, audit
    result = executor.execute(db, txn, action)

    if result["status"] == "EXECUTED":
        recon = reconciliation.reconcile(db, txn)
        if recon["final_status"] == "RECOVERED":
            audit.log_event(
                db, txn.id, "PAYMENT_RECOVERED",
                action=action, outcome="RECOVERED", recovered_amount=recon["recovered_amount"],
            )
        result["reconciliation"] = recon

    result["transaction_id"] = txn.transaction_ref
    return result


@app.post("/reviews/{review_id}/reject")
def reject_review(review_id: int, db: Session = Depends(get_db)):
    review = db.query(ManualReview).filter(ManualReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    review.status = "REJECTED"
    review.reviewed_by = "merchant"
    review.reviewed_at = datetime.utcnow()

    txn = db.query(Transaction).filter(Transaction.id == review.transaction_id).first()
    if txn:
        txn.recovery_status = "STOPPED"

    db.commit()
    return {"review_id": review_id, "status": "REJECTED"}


@app.get("/policies", response_model=list[PolicyOut])
def get_policies(db: Session = Depends(get_db)):
    return db.query(Policy).all()


@app.put("/policies", response_model=PolicyOut)
def update_policy(update: PolicyUpdate, db: Session = Depends(get_db)):
    pol = db.query(Policy).first()
    if not pol:
        raise HTTPException(status_code=404, detail="No policy configured.")

    data = update.dict(exclude_unset=True)
    for key, value in data.items():
        setattr(pol, key, value)

    db.commit()
    db.refresh(pol)
    return pol


@app.get("/audit", response_model=list[AuditEventOut])
def get_audit(db: Session = Depends(get_db)):
    return db.query(RecoveryEvent).order_by(RecoveryEvent.executed_at.desc()).all()


@app.post("/seed")
def reseed():
    seed_module.seed()
    return {"status": "ok", "message": "Database reseeded."}