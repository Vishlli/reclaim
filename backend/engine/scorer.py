"""
scorer.py

Calculates a transparent, deterministic Recovery Score for a transaction.

IMPORTANT: This is a prioritization heuristic, NOT a statistical
probability and NOT the output of a trained ML model. Every point
added or subtracted is traceable to a named factor, which is exposed
in the response so the score is fully explainable.
"""

from models import Transaction
from engine.detector import DetectionResult

BASE_SCORE = 50


def score_transaction(transaction: Transaction, detection: DetectionResult) -> dict:
    score = BASE_SCORE
    factors = []

    # Already recovered — score is meaningless, zero it out
    if detection.category == "ALREADY_RECOVERED":
        return {
            "score": 0,
            "label": "NOT ELIGIBLE",
            "factors": ["Transaction already recovered"],
        }

    # Too many attempts — heavily penalize regardless of other factors
    if transaction.attempt_count >= 3:
        score -= 40
        factors.append("3+ attempts (-40)")

    elif transaction.attempt_count == 2:
        score -= 15
        factors.append("Repeated failure, 2nd attempt (-15)")

    elif transaction.attempt_count == 1:
        score += 15
        factors.append("First failed attempt (+15)")

    # Transient failures are more recoverable than hard declines
    if detection.category == "TRANSIENT_FAILURE":
        score += 20
        factors.append("Transient failure type (+20)")

    # Customer history — previous successful payments increase confidence
    if transaction.customer_previous_successes > 0:
        score += 10
        factors.append(f"Previous successful customer, {transaction.customer_previous_successes} order(s) (+10)")

    # Recency — recent failures are more actionable than stale ones
    from datetime import datetime, timedelta
    if transaction.last_attempt_at and (datetime.utcnow() - transaction.last_attempt_at) < timedelta(hours=24):
        score += 5
        factors.append("Recent failure, within 24h (+5)")

    # Low-value transactions: intervention cost likely exceeds recovery value
    if transaction.amount < 500:
        score -= 20
        factors.append("Low transaction value vs. intervention cost (-20)")

    # High-value transactions get routed to review, not blindly boosted
    if transaction.amount > 25000:
        factors.append("High value — routed to manual review, score de-prioritized for auto-action")

    score = max(0, min(100, score))

    if score >= 65:
        label = "HIGH PRIORITY"
    elif score >= 35:
        label = "MEDIUM PRIORITY"
    else:
        label = "LOW PRIORITY"

    if not detection.eligible:
        label = "NOT ELIGIBLE"

    return {
        "score": score,
        "label": label,
        "factors": factors,
    }