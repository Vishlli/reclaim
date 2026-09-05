from engine import detector, scorer, recommender, policy as policy_engine, executor, reconciliation
from services import transaction_service
from tests.conftest import make_transaction


# ---------- Detector ----------

def test_transient_failure_detected(db):
    txn = make_transaction(db, failure_code="payment_timeout", attempts=1)
    result = detector.detect(txn)
    assert result.category == "TRANSIENT_FAILURE"
    assert result.eligible is True


def test_repeated_failure_detected(db):
    txn = make_transaction(db, failure_code="gateway_declined", attempts=2)
    result = detector.detect(txn)
    assert result.category == "REPEATED_FAILURE"
    assert result.eligible is True


def test_too_many_attempts_stops(db):
    txn = make_transaction(db, failure_code="gateway_declined", attempts=3)
    result = detector.detect(txn)
    assert result.category == "TOO_MANY_ATTEMPTS"
    assert result.suggested_next_step == "STOP"
    assert result.eligible is False


def test_already_recovered_no_action(db):
    txn = make_transaction(db, status="SUCCESS", recovery_status="RECOVERED")
    result = detector.detect(txn)
    assert result.category == "ALREADY_RECOVERED"
    assert result.suggested_next_step == "NO_ACTION"
    assert result.eligible is False


def test_high_value_routes_to_manual_review(db):
    txn = make_transaction(db, amount=30000, failure_code="gateway_declined", attempts=1)
    result = detector.detect(txn)
    assert result.category == "HIGH_VALUE_FAILURE"
    assert result.suggested_next_step == "MANUAL_REVIEW"


# ---------- Policy engine ----------

def test_policy_allows_normal_action(db):
    txn = make_transaction(db, amount=5000, failure_code="payment_timeout", attempts=1)
    pol = db.query(__import__("models").Policy).first()
    detection = detector.detect(txn)
    recommendation = recommender.recommend(txn, detection)
    decision = policy_engine.evaluate(txn, recommendation, pol)
    assert decision["decision"] == "ALLOWED"


def test_policy_blocks_when_max_attempts_exceeded(db):
    txn = make_transaction(db, amount=5000, failure_code="gateway_declined", attempts=2)
    pol = db.query(__import__("models").Policy).first()
    detection = detector.detect(txn)
    recommendation = recommender.recommend(txn, detection)
    decision = policy_engine.evaluate(txn, recommendation, pol)
    assert decision["decision"] == "BLOCKED"
    assert decision["alternative_action"] == "STOP"


def test_ai_discount_recommendation_blocked_by_policy(db):
    txn = make_transaction(db, ref="DEMO-HERO", amount=4999, failure_code="gateway_declined", attempts=1, prev_success=3)
    pol = db.query(__import__("models").Policy).first()
    detection = detector.detect(txn)
    recommendation = recommender.recommend(txn, detection)
    assert recommendation["disallowed_component"] == "10% discount"

    decision = policy_engine.evaluate(txn, recommendation, pol)
    assert decision["decision"] == "BLOCKED"
    assert "discount" in decision["reason"].lower()
    assert decision["alternative_action"] == recommendation["recommended_action"]


# ---------- Executor / idempotency ----------

def test_duplicate_action_prevented(db):
    txn = make_transaction(db, amount=5000, failure_code="payment_timeout", attempts=1)
    first = executor.execute(db, txn, "RETRY")
    assert first["status"] == "EXECUTED"

    second = executor.execute(db, txn, "RETRY")
    assert second["status"] == "DUPLICATE_PREVENTED"


def test_failed_action_creates_manual_review(db):
    txn = make_transaction(db, ref="DEMO-FAIL", amount=3499, failure_code="payment_timeout", attempts=1)
    result = executor.execute(db, txn, "RETRY")
    assert result["status"] == "FAILED"

    from models import ManualReview
    review = db.query(ManualReview).filter(ManualReview.transaction_id == txn.id).first()
    assert review is not None
    assert review.status == "AWAITING_MERCHANT_APPROVAL"


def test_successful_recovery_updates_recovered_amount(db):
    txn = make_transaction(db, amount=4999, failure_code="payment_timeout", attempts=1)
    executor.execute(db, txn, "GENERATE_PAYMENT_LINK")
    recon = reconciliation.reconcile(db, txn)
    assert recon["final_status"] == "RECOVERED"
    assert recon["recovered_amount"] == 4999


# ---------- Dashboard ----------

def test_dashboard_metrics_calculate_correctly(db):
    make_transaction(db, ref="TXN-A", amount=1000, status="FAILED", attempts=1)
    make_transaction(db, ref="TXN-B", amount=2000, status="SUCCESS", recovery_status="RECOVERED", attempts=1)

    metrics = transaction_service.compute_dashboard_metrics(db)
    assert metrics["transactions_analyzed"] == 2
    assert metrics["environment"] == "SIMULATED_TEST"