"""
recommender.py

Turns a detection result + recovery score into a recommended action.

IMPORTANT SEPARATION OF CONCERNS:
- This module (and detector.py, scorer.py) is the DETERMINISTIC layer.
  It decides eligibility, category, score, and the base recommended action.
- The optional AI/LLM layer below ONLY generates a human-readable
  explanation of the recommendation already decided deterministically.
  It does NOT choose the action and it CANNOT authorize money movement.
- The policy engine (policy.py) always has final authority over whether
  the recommended action is allowed to execute.
"""
import anthropic
import os
from models import Transaction
from engine.detector import DetectionResult

ALLOWED_ACTIONS = {
    "RETRY",
    "GENERATE_PAYMENT_LINK",
    "ALTERNATE_PAYMENT_ROUTE",
    "MANUAL_REVIEW",
    "STOP",
    "NO_ACTION",
}


def _base_recommendation(transaction: Transaction, detection: DetectionResult) -> dict:
    """
    Deterministic mapping from detection category -> recommended action.
    This is the ONLY thing that decides the action. Nothing downstream
    can override this except the policy engine (which can only BLOCK
    or substitute an ALLOWED alternative, never invent a new action).
    """
    mapping = {
        "ALREADY_RECOVERED": ("NO_ACTION", "Payment has already succeeded; no further action required."),
        "TOO_MANY_ATTEMPTS": ("STOP", "Maximum recovery attempts reached; further contact is not permitted."),
        "LOW_VALUE": ("STOP", "Expected intervention cost is not justified by transaction value."),
        "HIGH_VALUE_FAILURE": ("MANUAL_REVIEW", "Transaction value requires human approval before any action."),
        "REPEATED_FAILURE": ("ALTERNATE_PAYMENT_ROUTE", "Same failure has recurred; suggest a different payment route."),
        "TRANSIENT_FAILURE": ("RETRY", "Failure code suggests a temporary issue; retry is likely to succeed."),
        "CHECKOUT_ABANDONMENT": ("GENERATE_PAYMENT_LINK", "Payment was never completed; send a link to resume checkout."),
    }
    action, reason = mapping.get(detection.category, ("MANUAL_REVIEW", "Unrecognized case; routed to human review."))
    return {"action": action, "reason": reason}


def _evidence(transaction: Transaction, detection: DetectionResult) -> list:
    ev = [
        f"Attempt count: {transaction.attempt_count}",
        f"Failure code: {transaction.failure_code or 'n/a'}",
        f"Transaction value: ₹{transaction.amount:,.0f}",
    ]
    if transaction.customer_previous_successes > 0:
        ev.append(f"Previous successful orders: {transaction.customer_previous_successes}")
    ev.append(f"Category: {detection.category}")
    return ev


def _fallback_ai_explanation(transaction: Transaction, detection: DetectionResult, action: str) -> str:
    """
    Deterministic, template-based explanation used when no LLM provider
    is configured (or the LLM call fails). The app must remain fully
    usable without an API key — this is the guaranteed fallback.
    """
    return (
        f"Based on {transaction.attempt_count} attempt(s), failure code "
        f"'{transaction.failure_code or 'n/a'}', and a transaction value of "
        f"₹{transaction.amount:,.0f}, the recommended action is {action.replace('_', ' ').title()}."
    )

import anthropic


class AIExplainerInterface:
    """
    Abstraction so the LLM provider can be swapped without touching the
    deterministic engine. The LLM is ONLY ever asked to explain a
    decision that has already been made — never to choose the action
    itself, and its output is never trusted for financial authorization.
    """

    def explain(self, transaction: Transaction, detection: DetectionResult, action: str, evidence: list) -> str:
        raise NotImplementedError


class DeterministicFallbackExplainer(AIExplainerInterface):
    def explain(self, transaction, detection, action, evidence):
        return _fallback_ai_explanation(transaction, detection, action)


class ClaudeExplainer(AIExplainerInterface):
    """
    Real LLM-backed explainer using the Anthropic API. Generates a
    human-readable explanation ONLY — the action itself is passed in
    already-decided and is never modified based on the LLM's output.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def explain(self, transaction, detection, action, evidence):
        prompt = (
            "You are explaining a payment recovery decision to a merchant. "
            "The action has ALREADY been decided by a deterministic system — "
            "you are only summarizing WHY, in 1-2 plain sentences. "
            "Do not suggest a different action. Do not mention discounts. "
            "Do not invent facts not present in the evidence below.\n\n"
            f"Transaction category: {detection.category}\n"
            f"Decided action: {action}\n"
            f"Evidence: {', '.join(evidence)}\n\n"
            "Write the explanation now."
        )
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()
            return text if text else _fallback_ai_explanation(transaction, detection, action)
        except Exception:
            # Never let an LLM/network failure break the recovery flow.
            return _fallback_ai_explanation(transaction, detection, action)


def get_ai_explainer() -> AIExplainerInterface:
    """
    Returns a real Claude-backed explainer if ANTHROPIC_API_KEY is set,
    otherwise the deterministic fallback. The app must remain fully
    usable with zero API keys configured — this guarantees that.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return ClaudeExplainer()
        except Exception:
            return DeterministicFallbackExplainer()
    return DeterministicFallbackExplainer()

def recommend(transaction: Transaction, detection: DetectionResult) -> dict:
    base = _base_recommendation(transaction, detection)
    action = base["action"]
    reason = base["reason"]
    evidence = _evidence(transaction, detection)

    explainer = get_ai_explainer()
    ai_explanation = explainer.explain(transaction, detection, action, evidence)

    result = {
        "recommended_action": action,
        "reasoning": reason,
        "evidence": evidence,
        "ai_explanation": ai_explanation,
        "disallowed_component": None,
    }

    # ---- DEMO-HERO special case ----
    # For the designated demo transaction, the AI layer proposes an
    # intentionally out-of-policy embellishment (a discount) alongside
    # the valid action, purely to demonstrate the policy engine blocking
    # it. The deterministic action itself (GENERATE_PAYMENT_LINK /
    # ALTERNATE_PAYMENT_ROUTE) is unaffected — only the "extra" the AI
    # layer tacked on gets blocked downstream.
    if getattr(transaction, "transaction_ref", None) == "DEMO-HERO":
        result["disallowed_component"] = "10% discount"
        result["reasoning"] += " (AI layer additionally suggested a 10% discount incentive.)"

    assert action in ALLOWED_ACTIONS, f"Recommender produced an invalid action: {action}"

    return result