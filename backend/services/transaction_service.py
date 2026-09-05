"""
transaction_service.py

Read-side helpers for fetching transactions and computing dashboard
metrics directly from the database. No decision logic lives here.
"""

from sqlalchemy.orm import Session
from models import Transaction, RecoveryEvent


def get_transaction_by_ref(db: Session, transaction_ref: str) -> Transaction:
    return db.query(Transaction).filter(Transaction.transaction_ref == transaction_ref).first()


def list_transactions(db: Session):
    return db.query(Transaction).order_by(Transaction.created_at.desc()).all()


def compute_dashboard_metrics(db: Session) -> dict:
    all_txns = db.query(Transaction).all()
    transactions_analyzed = len(all_txns)

    revenue_at_risk = sum(
        t.amount for t in all_txns
        if t.status in ("FAILED", "ABANDONED") and t.recovery_status != "RECOVERED"
    )

    eligible_cases = sum(
        1 for t in all_txns
        if t.recovery_status in ("UNRESOLVED", "ELIGIBLE", "ACTION_TAKEN", "MANUAL_REVIEW")
        and t.status in ("FAILED", "ABANDONED")
        and t.attempt_count < 3
        and t.amount >= 300
    )

    actions_executed = (
        db.query(RecoveryEvent)
        .filter(RecoveryEvent.event_type == "ACTION_EXECUTED")
        .count()
    )

    successful_recoveries = sum(1 for t in all_txns if t.recovery_status == "RECOVERED")

    recovered_revenue = sum(
        e.recovered_amount or 0
        for e in db.query(RecoveryEvent).filter(RecoveryEvent.recovered_amount > 0).all()
    )

    return {
        "transactions_analyzed": transactions_analyzed,
        "revenue_at_risk": round(revenue_at_risk, 2),
        "eligible_cases": eligible_cases,
        "actions_executed": actions_executed,
        "successful_recoveries": successful_recoveries,
        "recovered_revenue": round(recovered_revenue, 2),
        "environment": "SIMULATED_TEST",
    }