"""
reconciliation.py

Compares a transaction's original state against its recovery action
outcome and determines the final reconciled state + recovered amount.

This is the source of truth for "was money actually recovered" —
it never trusts a single event in isolation, it looks at the
transaction's current recovery_status plus its most recent
successful RecoveryEvent.
"""

from sqlalchemy.orm import Session
from models import Transaction, RecoveryEvent


def reconcile(db: Session, transaction: Transaction) -> dict:
    """
    Returns:
        {
            "transaction_id": str,
            "original_amount": float,
            "final_status": "RECOVERED" | "STOPPED" | "MANUAL_REVIEW" | "UNRESOLVED" | "ACTION_TAKEN",
            "recovered_amount": float
        }
    """
    # If a transaction was already SUCCESS/RECOVERED before any action, stop immediately.
    if transaction.status == "SUCCESS" or transaction.recovery_status == "RECOVERED":
        return {
            "transaction_id": transaction.transaction_ref,
            "original_amount": transaction.amount,
            "final_status": "RECOVERED",
            "recovered_amount": transaction.amount,
        }

    latest_success = (
        db.query(RecoveryEvent)
        .filter(
            RecoveryEvent.transaction_id == transaction.id,
            RecoveryEvent.outcome == "SUCCESS",
            RecoveryEvent.event_type == "ACTION_EXECUTED",
        )
        .order_by(RecoveryEvent.executed_at.desc())
        .first()
    )

    if latest_success and latest_success.action in ("RETRY", "GENERATE_PAYMENT_LINK", "ALTERNATE_PAYMENT_ROUTE"):
        # Mark as recovered and persist the recovered amount on the event + transaction.
        latest_success.recovered_amount = transaction.amount
        transaction.recovery_status = "RECOVERED"
        db.commit()
        return {
            "transaction_id": transaction.transaction_ref,
            "original_amount": transaction.amount,
            "final_status": "RECOVERED",
            "recovered_amount": transaction.amount,
        }

    return {
        "transaction_id": transaction.transaction_ref,
        "original_amount": transaction.amount,
        "final_status": transaction.recovery_status,
        "recovered_amount": 0,
    }