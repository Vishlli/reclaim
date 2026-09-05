"""
detector.py

Classifies a transaction into a recovery-relevant category based on
its raw fields (status, attempts, amount, failure_code).

This module is purely deterministic. It does not calculate scores
or recommend actions — that happens in scorer.py and recommender.py.
"""

from models import Transaction

# Failure codes we treat as "transient" (temporary, likely to succeed on retry)
TRANSIENT_CODES = {"payment_timeout", "network_error", "gateway_unavailable"}

# Failure codes we treat as "hard" repeated failures (same root cause recurring)
REPEATED_FAILURE_CODES = {"payment_failed", "gateway_declined", "insufficient_funds"}


class DetectionResult:
    def __init__(self, eligible: bool, category: str, reason: str, suggested_next_step: str):
        self.eligible = eligible
        self.category = category
        self.reason = reason
        self.suggested_next_step = suggested_next_step

    def to_dict(self):
        return {
            "eligible": self.eligible,
            "category": self.category,
            "reason": self.reason,
            "suggested_next_step": self.suggested_next_step,
        }


def detect(transaction: Transaction) -> DetectionResult:
    """
    Categorize a transaction for recovery purposes.

    Categories:
      - ALREADY_RECOVERED
      - TOO_MANY_ATTEMPTS
      - HIGH_VALUE_FAILURE
      - REPEATED_FAILURE
      - TRANSIENT_FAILURE
      - CHECKOUT_ABANDONMENT
      - LOW_VALUE
      - NOT_ELIGIBLE (fallback)
    """

    # Already succeeded — nothing to do
    if transaction.status == "SUCCESS" or transaction.recovery_status == "RECOVERED":
        return DetectionResult(
            eligible=False,
            category="ALREADY_RECOVERED",
            reason="Transaction has already succeeded.",
            suggested_next_step="NO_ACTION",
        )

    # Too many attempts — stop, don't keep hammering the customer/gateway
    if transaction.attempt_count >= 3:
        return DetectionResult(
            eligible=False,
            category="TOO_MANY_ATTEMPTS",
            reason=f"{transaction.attempt_count} failed attempts recorded; further attempts are not permitted.",
            suggested_next_step="STOP",
        )

    # High value — always route to human review regardless of failure type
    if transaction.amount > 25000:
        return DetectionResult(
            eligible=True,
            category="HIGH_VALUE_FAILURE",
            reason=f"Transaction value ₹{transaction.amount:,.0f} exceeds high-value threshold.",
            suggested_next_step="MANUAL_REVIEW",
        )

    # Low value — intervention cost may exceed the benefit
    if transaction.amount < 300:
        return DetectionResult(
            eligible=False,
            category="LOW_VALUE",
            reason=f"Transaction value ₹{transaction.amount:,.0f} is too low to justify recovery cost.",
            suggested_next_step="STOP",
        )

    # Checkout abandonment — no failure code, but never completed
    if transaction.status == "ABANDONED":
        return DetectionResult(
            eligible=True,
            category="CHECKOUT_ABANDONMENT",
            reason="Payment was initiated but never completed.",
            suggested_next_step="GENERATE_PAYMENT_LINK",
        )

    # Repeated failure (2nd attempt, same category of hard failure)
    if transaction.attempt_count == 2 and transaction.failure_code in REPEATED_FAILURE_CODES:
        return DetectionResult(
            eligible=True,
            category="REPEATED_FAILURE",
            reason=f"Second consecutive failure with code '{transaction.failure_code}'.",
            suggested_next_step="ALTERNATE_PAYMENT_ROUTE",
        )

    # Transient failure (first attempt, temporary-looking cause)
    if transaction.failure_code in TRANSIENT_CODES:
        return DetectionResult(
            eligible=True,
            category="TRANSIENT_FAILURE",
            reason=f"Failure code '{transaction.failure_code}' is typically temporary.",
            suggested_next_step="RETRY",
        )

    # Fallback: failed but doesn't cleanly match a category above
    return DetectionResult(
        eligible=True,
        category="REPEATED_FAILURE",
        reason=f"Failed payment with code '{transaction.failure_code}', attempt {transaction.attempt_count}.",
        suggested_next_step="GENERATE_PAYMENT_LINK",
    )