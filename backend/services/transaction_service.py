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

    # Source of truth for "recovered" is a real RecoveryEvent with a
    # recovered_amount, not just a transaction's recovery_status flag —
    # a transaction can be marked RECOVERED because it simply succeeded
    # on its own (never entered the recovery pipeline), and that should
    # not be counted as a RECLAIM recovery. Dedupe by transaction so a
    # transaction is only ever counted once even if it has multiple
    # recovered events (shouldn't happen given idempotency, but be safe).
    recovered_amount_by_txn = {}
    for e in db.query(RecoveryEvent).filter(RecoveryEvent.recovered_amount > 0).all():
        recovered_amount_by_txn[e.transaction_id] = e.recovered_amount

    successful_recoveries = len(recovered_amount_by_txn)
    recovered_revenue = sum(recovered_amount_by_txn.values())

    return {
        "transactions_analyzed": transactions_analyzed,
        "revenue_at_risk": round(revenue_at_risk, 2),
        "eligible_cases": eligible_cases,
        "actions_executed": actions_executed,
        "successful_recoveries": successful_recoveries,
        "recovered_revenue": round(recovered_revenue, 2),
        "environment": "SIMULATED_TEST",
    }