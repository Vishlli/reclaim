"""
recovery_service.py

Orchestrates the full recovery pipeline:
Detect -> Score -> Recommend -> Policy Gate -> (optionally) Execute -> Reconcile

Every step writes an audit event. This is the module main.py calls
for POST /recovery/analyze/{id} and POST /recovery/execute/{id}.
"""

from sqlalchemy.orm import Session

from models import Transaction, Policy, ManualReview
from engine import detector, scorer, recommender, policy as policy_engine, executor, reconciliation, audit


def _get_policy(db: Session) -> Policy:
    pol = db.query(Policy).first()
    if not pol:
        raise RuntimeError("No policy configured. Run seed.py first.")
    return pol


def analyze_transaction(db: Session, transaction: Transaction) -> dict:
    detection = detector.detect(transaction)

    audit.log_event(
        db, transaction.id, "TRANSACTION_DETECTED",
        reason=detection.reason, outcome=detection.category,
    )

    score_result = scorer.score_transaction(transaction, detection)
    recommendation = recommender.recommend(transaction, detection)

    audit.log_event(
        db, transaction.id, "AI_RECOMMENDATION",
        action=recommendation["recommended_action"], reason=recommendation["reasoning"],
    )

    pol = _get_policy(db)
    policy_decision = policy_engine.evaluate(transaction, recommendation, pol)

    if policy_decision["decision"] == "BLOCKED":
        audit.log_event(
            db, transaction.id, "POLICY_BLOCKED",
            action=recommendation["recommended_action"], reason=policy_decision["reason"],
            policy_result="BLOCKED",
        )
    else:
        audit.log_event(
            db, transaction.id, "POLICY_EVALUATION",
            action=recommendation["recommended_action"], reason=policy_decision["reason"],
            policy_result=policy_decision["decision"],
        )

    if policy_decision["decision"] == "MANUAL_REVIEW":
        existing_review = (
            db.query(ManualReview)
            .filter(ManualReview.transaction_id == transaction.id, ManualReview.status == "AWAITING_MERCHANT_APPROVAL")
            .first()
        )
        if not existing_review:
            review = ManualReview(
                transaction_id=transaction.id,
                reason=policy_decision["reason"],
                recommendation=recommendation["recommended_action"],
                status="AWAITING_MERCHANT_APPROVAL",
            )
            db.add(review)
            audit.log_event(db, transaction.id, "MANUAL_REVIEW_CREATED", reason=policy_decision["reason"])
        transaction.recovery_status = "MANUAL_REVIEW"
        db.commit()

    return {
        "transaction_id": transaction.transaction_ref,
        "recovery_score": score_result,
        "recommendation": recommendation,
        "policy_decision": policy_decision,
        "environment": "SIMULATED_TEST",
    }


def execute_transaction(db: Session, transaction: Transaction) -> dict:
    analysis = analyze_transaction(db, transaction)
    decision = analysis["policy_decision"]["decision"]

    if decision == "MANUAL_REVIEW":
        return {
            "transaction_id": transaction.transaction_ref,
            "status": "AWAITING_APPROVAL",
            "message": "Transaction requires manual merchant approval before execution.",
        }

    action_to_run = (
        analysis["policy_decision"]["alternative_action"]
        if analysis["policy_decision"]["decision"] == "BLOCKED"
        else analysis["recommendation"]["recommended_action"]
    )

    if analysis["policy_decision"]["decision"] == "BLOCKED" and not action_to_run:
        return {
            "transaction_id": transaction.transaction_ref,
            "status": "FAILED",
            "message": "Action blocked by policy and no allowed alternative available.",
        }

    result = executor.execute(db, transaction, action_to_run)

    if result["status"] == "DUPLICATE_PREVENTED":
        audit.log_event(
            db, transaction.id, "DUPLICATE_PREVENTED",
            action=action_to_run, reason=result["message"],
            idempotency_key=result.get("idempotency_key"),
        )
    elif result["status"] == "FAILED":
        pass  # executor.py already logs ACTION_FAILED + creates ManualReview
    elif result["status"] == "EXECUTED":
        recon = reconciliation.reconcile(db, transaction)
        if recon["final_status"] == "RECOVERED":
            audit.log_event(
                db, transaction.id, "PAYMENT_RECOVERED",
                action=action_to_run, outcome="RECOVERED",
                recovered_amount=recon["recovered_amount"],
            )
        result["reconciliation"] = recon

    result["transaction_id"] = transaction.transaction_ref
    return result