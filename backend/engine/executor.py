"""
executor.py

Executes ONLY actions that have already been approved by policy.py.
This module never makes authorization decisions — it assumes the
caller has already checked policy_decision["decision"] == "ALLOWED".

Includes:
- A PaymentGateway abstraction (so a real Razorpay Test Mode connector
  can be dropped in later without touching this file's control flow).
- Idempotency: the same recovery action on the same transaction will
  never execute twice.
- A controlled, deterministic failure path for the DEMO-FAIL scenario.
"""

import hashlib
from datetime import datetime
from sqlalchemy.orm import Session

from models import Transaction, RecoveryEvent, ManualReview

SIMULATED_TAG = "[SIMULATED]"


# ---------------------------------------------------------------------------
# Gateway abstraction — swap in a real Razorpay Test Mode client later
# without changing anything below this class.
# ---------------------------------------------------------------------------

class PaymentGateway:
    def generate_payment_link(self, transaction: Transaction) -> dict:
        raise NotImplementedError

    def retry_payment(self, transaction: Transaction) -> dict:
        raise NotImplementedError

    def alternate_route(self, transaction: Transaction) -> dict:
        raise NotImplementedError


class SimulatedGateway(PaymentGateway):
    """
    Fully simulated gateway. No real network calls, no real money.
    DEMO-FAIL is hardcoded to fail here on purpose, to demonstrate
    safe failure handling.
    """

    def generate_payment_link(self, transaction: Transaction) -> dict:
        if transaction.transaction_ref == "DEMO-FAIL":
            return {"success": False, "error": "SIMULATED_GATEWAY_ERROR: payment link service unavailable"}
        ref = f"plink_test_{abs(hash(transaction.transaction_ref)) % 100000}"
        return {"success": True, "reference": ref, "message": f"{SIMULATED_TAG} Payment link generated"}

    def retry_payment(self, transaction: Transaction) -> dict:
        if transaction.transaction_ref == "DEMO-FAIL":
            return {"success": False, "error": "SIMULATED_GATEWAY_ERROR: retry rejected"}
        return {"success": True, "reference": f"retry_test_{transaction.id}", "message": f"{SIMULATED_TAG} Retry submitted"}

    def alternate_route(self, transaction: Transaction) -> dict:
        if transaction.transaction_ref == "DEMO-FAIL":
            return {"success": False, "error": "SIMULATED_GATEWAY_ERROR: alternate route unavailable"}
        return {"success": True, "reference": f"altroute_test_{transaction.id}", "message": f"{SIMULATED_TAG} Alternate route initiated"}


# Placeholder for future real integration — must implement the same
# interface as SimulatedGateway. Never used until explicitly wired in.
class RazorpayTestGateway(PaymentGateway):
    def generate_payment_link(self, transaction: Transaction) -> dict:
        raise NotImplementedError("Razorpay Test Mode connector not yet implemented.")

    def retry_payment(self, transaction: Transaction) -> dict:
        raise NotImplementedError("Razorpay Test Mode connector not yet implemented.")

    def alternate_route(self, transaction: Transaction) -> dict:
        raise NotImplementedError("Razorpay Test Mode connector not yet implemented.")


def get_gateway() -> PaymentGateway:
    return SimulatedGateway()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def make_idempotency_key(transaction: Transaction, action: str) -> str:
    """
    Deterministic key: same transaction + same action always produces
    the same key. This is what lets us detect duplicate execution.
    """
    raw = f"{transaction.transaction_ref}:{action}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _find_existing_event(db: Session, transaction: Transaction, idempotency_key: str):
    return (
        db.query(RecoveryEvent)
        .filter(
            RecoveryEvent.transaction_id == transaction.id,
            RecoveryEvent.idempotency_key == idempotency_key,
            RecoveryEvent.event_type.in_(["ACTION_EXECUTED", "ACTION_FAILED"]),
        )
        .first()
    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def execute(db: Session, transaction: Transaction, action: str) -> dict:
    """
    Executes an approved action. Assumes the caller already confirmed
    policy allowed this. Returns a result dict describing what happened.
    """
    idempotency_key = make_idempotency_key(transaction, action)

    # --- Idempotency check: has this exact action already been attempted (success or failure)? ---
    existing = _find_existing_event(db, transaction, idempotency_key)
    if existing:
        already_failed = existing.event_type == "ACTION_FAILED"
        return {
            "status": "DUPLICATE_PREVENTED",
            "message": (
                "This action previously failed and was routed to manual review; "
                "it will not be retried automatically."
                if already_failed else
                "Identical recovery action already executed for this transaction."
            ),
            "action": action,
            "idempotency_key": idempotency_key,
        }

    gateway = get_gateway()

    if action == "STOP":
        event = RecoveryEvent(
            transaction_id=transaction.id,
            event_type="ACTION_EXECUTED",
            action="STOP_RECOVERY",
            reason="Recovery stopped per policy/detection rules.",
            policy_result="ALLOWED",
            outcome="STOPPED",
            idempotency_key=idempotency_key,
        )
        db.add(event)
        transaction.recovery_status = "STOPPED"
        db.commit()
        return {"status": "EXECUTED", "action": "STOP_RECOVERY", "outcome": "STOPPED", "idempotency_key": idempotency_key}

    if action == "NO_ACTION":
        return {"status": "EXECUTED", "action": "NO_ACTION", "outcome": "NO_ACTION_NEEDED", "idempotency_key": idempotency_key}

    # --- Actions that call the (simulated) gateway ---
    gateway_call = {
        "RETRY": gateway.retry_payment,
        "GENERATE_PAYMENT_LINK": gateway.generate_payment_link,
        "ALTERNATE_PAYMENT_ROUTE": gateway.alternate_route,
    }.get(action)

    if gateway_call is None:
        return {"status": "FAILED", "message": f"Unknown or unsupported action: {action}", "action": action}

    result = gateway_call(transaction)

    if not result.get("success"):
        # --- Controlled failure path (spec requirement) ---
        failure_event = RecoveryEvent(
            transaction_id=transaction.id,
            event_type="ACTION_FAILED",
            action=action,
            reason=result.get("error", "Unknown gateway failure"),
            policy_result="ALLOWED",
            outcome="FAILED",
            idempotency_key=idempotency_key,
        )
        db.add(failure_event)

        review = ManualReview(
            transaction_id=transaction.id,
            reason=f"Recovery action '{action}' failed: {result.get('error')}",
            recommendation=action,
            status="AWAITING_MERCHANT_APPROVAL",
        )
        db.add(review)
        transaction.recovery_status = "MANUAL_REVIEW"
        db.commit()

        return {
            "status": "FAILED",
            "action": action,
            "message": f"{SIMULATED_TAG} Action failed safely. No duplicate action will be attempted. Case moved to manual review.",
            "idempotency_key": idempotency_key,
        }

    # --- Success path ---
    event = RecoveryEvent(
        transaction_id=transaction.id,
        event_type="ACTION_EXECUTED",
        action=action,
        reason=result.get("message"),
        policy_result="ALLOWED",
        outcome="SUCCESS",
        idempotency_key=idempotency_key,
    )
    db.add(event)
    transaction.recovery_status = "ACTION_TAKEN"
    db.commit()

    return {
        "status": "EXECUTED",
        "action": action,
        "outcome": "SUCCESS",
        "reference": result.get("reference"),
        "message": result.get("message"),
        "idempotency_key": idempotency_key,
    }