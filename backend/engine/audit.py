"""
audit.py

Single shared helper for writing audit-relevant RecoveryEvent rows.
Other engine modules (detector, recommender, policy) call this so
every meaningful step of the pipeline is logged consistently, even
steps that don't themselves result in a financial action.
"""

from sqlalchemy.orm import Session
from models import RecoveryEvent


VALID_EVENT_TYPES = {
    "TRANSACTION_DETECTED",
    "AI_RECOMMENDATION",
    "POLICY_EVALUATION",
    "POLICY_BLOCKED",
    "ACTION_APPROVED",
    "ACTION_EXECUTED",
    "ACTION_FAILED",
    "DUPLICATE_PREVENTED",
    "PAYMENT_RECOVERED",
    "MANUAL_REVIEW_CREATED",
}


def log_event(
    db: Session,
    transaction_id: int,
    event_type: str,
    action: str = None,
    reason: str = None,
    policy_result: str = None,
    outcome: str = None,
    recovered_amount: float = 0,
    idempotency_key: str = None,
    commit: bool = True,
) -> RecoveryEvent:
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"Unknown audit event_type: {event_type}")

    event = RecoveryEvent(
        transaction_id=transaction_id,
        event_type=event_type,
        action=action,
        reason=reason,
        policy_result=policy_result,
        outcome=outcome,
        recovered_amount=recovered_amount,
        idempotency_key=idempotency_key,
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    return event