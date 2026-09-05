"""
policy.py

The Policy Engine — final authority over whether a recommended
recovery action is permitted to execute.

CRITICAL RULE: The AI/recommender layer proposes. This module decides.
No action reaches executor.py without passing through here first.
"""

from datetime import datetime, time
from models import Transaction, Policy


def _within_contact_window(policy: Policy) -> bool:
    now = datetime.now().time()
    start = time.fromisoformat(policy.contact_start_time)
    end = time.fromisoformat(policy.contact_end_time)
    return start <= now <= end


def evaluate(transaction: Transaction, recommendation: dict, policy: Policy) -> dict:
    """
    Evaluates a recommended action against merchant policy.

    Returns:
        {
            "decision": "ALLOWED" | "BLOCKED" | "MANUAL_REVIEW",
            "reason": str,
            "alternative_action": str | None
        }
    """
    action = recommendation["recommended_action"]
    disallowed_component = recommendation.get("disallowed_component")

    if not policy.enabled:
        return {
            "decision": "BLOCKED",
            "reason": "Policy enforcement is currently disabled by the merchant.",
            "alternative_action": None,
        }

    # --- Rule 1: Already recovered / stopped cases pass through untouched ---
    if action in ("NO_ACTION", "STOP"):
        return {
            "decision": "ALLOWED",
            "reason": "No recovery action is being taken; nothing to gate.",
            "alternative_action": None,
        }

    # --- Rule 2: High-value / manual review requirement ---
    if action == "MANUAL_REVIEW" or transaction.amount >= policy.manual_approval_threshold:
        return {
            "decision": "MANUAL_REVIEW",
            "reason": f"Transaction value ₹{transaction.amount:,.0f} meets or exceeds the "
                      f"₹{policy.manual_approval_threshold:,.0f} manual approval threshold.",
            "alternative_action": action if action != "MANUAL_REVIEW" else None,
        }

    # --- Rule 3: Max attempts ---
    if transaction.attempt_count >= policy.max_attempts and action != "STOP":
        return {
            "decision": "BLOCKED",
            "reason": f"Attempt count ({transaction.attempt_count}) meets or exceeds the "
                      f"merchant's maximum of {policy.max_attempts} recovery attempts.",
            "alternative_action": "STOP",
        }

    # --- Rule 4: Discount / monetary concession block (THE DEMO CASE) ---
    if disallowed_component:
        return {
            "decision": "BLOCKED",
            "reason": f"AI suggested '{disallowed_component}', which exceeds merchant policy "
                      f"(maximum discount allowed: {policy.max_discount:.0f}%).",
            "alternative_action": action,  # the underlying action (e.g. GENERATE_PAYMENT_LINK) is still valid
        }

    # --- Rule 5: Contact time window (only relevant for customer-facing actions) ---
    if action in ("RETRY", "GENERATE_PAYMENT_LINK", "ALTERNATE_PAYMENT_ROUTE"):
        if not _within_contact_window(policy):
            return {
                "decision": "BLOCKED",
                "reason": f"Current time is outside the merchant's permitted contact window "
                          f"({policy.contact_start_time}–{policy.contact_end_time}).",
                "alternative_action": "MANUAL_REVIEW",
            }

    # --- Default: allowed as-is ---
    return{
        "decision": "ALLOWED",
        "reason": "Action complies with all merchant-configured policies.",
        "alternative_action": None,
    }