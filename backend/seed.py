"""
seed.py

Generates the SQLite database and populates it with ~150 synthetic
transactions across meaningful cohorts, plus a default Policy row.

Idempotent: running this multiple times will NOT duplicate data.
It wipes and recreates the relevant tables each time it runs.
"""

import random
from datetime import datetime, timedelta

from database import Base, engine, SessionLocal
from models import Transaction, Policy, RecoveryEvent, ManualReview
from engine.executor import make_idempotency_key, SIMULATED_TAG

random.seed(42)

FAILURE_CODES_TRANSIENT = ["payment_timeout", "network_error", "gateway_unavailable"]
FAILURE_CODES_HARD = ["payment_failed", "gateway_declined", "insufficient_funds"]
GATEWAYS = ["razorpay", "razorpay_upi", "razorpay_card", "netbanking"]

customer_names = [f"Customer {chr(65 + i)}" for i in range(26)] + [f"Customer {i}" for i in range(27, 60)]


def _rand_time_within(days_back: int) -> datetime:
    return datetime.utcnow() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def _make_txn(ref, customer, amount, status, failure_code, failure_reason, attempts, prev_success, recovery_status, created_offset_days=0):
    created = _rand_time_within(created_offset_days) if created_offset_days else datetime.utcnow()
    return Transaction(
        transaction_ref=ref,
        customer_id=customer,
        gateway=random.choice(GATEWAYS),
        amount=amount,
        currency="INR",
        status=status,
        failure_code=failure_code,
        failure_reason=failure_reason,
        attempt_count=attempts,
        created_at=created,
        last_attempt_at=created,
        customer_previous_successes=prev_success,
        recovery_status=recovery_status,
    )


def generate_transactions():
    txns = []
    recovered_cohort = []  # transactions that were genuinely recovered via the recovery pipeline
    counter = 10000

    def next_ref():
        nonlocal counter
        counter += 1
        return f"TXN-{counter}"

    # Cohort: Successful (25) — normal completed payments, not part of recovery pipeline
    for _ in range(25):
        txns.append(_make_txn(
            next_ref(), random.choice(customer_names), round(random.uniform(500, 15000), 2),
            "SUCCESS", None, None, 1, random.randint(0, 5), "RECOVERED", created_offset_days=5,
        ))

    # Cohort: Transient failure (30) — timeout/network/gateway issue, first attempt
    for _ in range(30):
        txns.append(_make_txn(
            next_ref(), random.choice(customer_names), round(random.uniform(500, 15000), 2),
            "FAILED", random.choice(FAILURE_CODES_TRANSIENT), "Temporary gateway/network issue",
            1, random.randint(0, 3), "UNRESOLVED", created_offset_days=3,
        ))

    # Cohort: Repeated failure (25) — 2 attempts, same hard failure code
    for _ in range(25):
        txns.append(_make_txn(
            next_ref(), random.choice(customer_names), round(random.uniform(1000, 20000), 2),
            "FAILED", random.choice(FAILURE_CODES_HARD), "Repeated decline from gateway",
            2, random.randint(0, 4), "UNRESOLVED", created_offset_days=2,
        ))

    # Cohort: Checkout abandonment (20) — initiated, never completed, no failure code
    for _ in range(20):
        txns.append(_make_txn(
            next_ref(), random.choice(customer_names), round(random.uniform(500, 12000), 2),
            "ABANDONED", None, "Checkout initiated but never completed",
            1, random.randint(0, 3), "UNRESOLVED", created_offset_days=2,
        ))

    # Cohort: High-value failure (12) — above ₹25,000
    for _ in range(12):
        txns.append(_make_txn(
            next_ref(), random.choice(customer_names), round(random.uniform(25001, 60000), 2),
            "FAILED", random.choice(FAILURE_CODES_HARD), "High-value payment failure",
            random.randint(1, 2), random.randint(0, 6), "UNRESOLVED", created_offset_days=1,
        ))

    # Cohort: Too many attempts (15) — 3+ failed attempts, must STOP
    for _ in range(15):
        txns.append(_make_txn(
            next_ref(), random.choice(customer_names), round(random.uniform(500, 10000), 2),
            "FAILED", random.choice(FAILURE_CODES_HARD), "Repeated failures across multiple attempts",
            random.randint(3, 5), random.randint(0, 2), "UNRESOLVED", created_offset_days=4,
        ))

    # Cohort: Low-value transaction (13) — intervention cost exceeds value
    for _ in range(13):
        txns.append(_make_txn(
            next_ref(), random.choice(customer_names), round(random.uniform(50, 299), 2),
            "FAILED", random.choice(FAILURE_CODES_TRANSIENT), "Low-value transient failure",
            1, random.randint(0, 2), "UNRESOLVED", created_offset_days=1,
        ))

    # Cohort: Already recovered (10) — failed, then later succeeded via a
    # RECLAIM recovery action. These are the ONLY transactions that should
    # count toward "Recovered Revenue" — track them separately so we can
    # seed matching RecoveryEvent rows (the dashboard's actual source of
    # truth for recovered revenue, see transaction_service.py).
    for _ in range(10):
        txn = _make_txn(
            next_ref(), random.choice(customer_names), round(random.uniform(500, 8000), 2),
            "SUCCESS", None, "Recovered after retry", 2, random.randint(0, 4), "RECOVERED", created_offset_days=3,
        )
        txns.append(txn)
        recovered_cohort.append(txn)

    # Remaining to reach ~150: mixed transient/repeated filler
    remaining = 150 - len(txns)
    for _ in range(remaining):
        txns.append(_make_txn(
            next_ref(), random.choice(customer_names), round(random.uniform(500, 18000), 2),
            "FAILED", random.choice(FAILURE_CODES_TRANSIENT + FAILURE_CODES_HARD), "Failed payment",
            random.choice([1, 2]), random.randint(0, 4), "UNRESOLVED", created_offset_days=2,
        ))

    # --- Fixed demo transactions ---
    txns.append(_make_txn(
        "DEMO-HERO", "Customer A", 4999, "FAILED", "gateway_declined",
        "Repeated UPI failure", 1, 3, "UNRESOLVED", created_offset_days=0,
    ))
    txns.append(_make_txn(
        "DEMO-FAIL", "Customer Z", 3499, "FAILED", "payment_timeout",
        "Transient failure, recovery action will fail on execution", 1, 1, "UNRESOLVED", created_offset_days=0,
    ))

    return txns, recovered_cohort


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db.query(RecoveryEvent).delete()
        db.query(ManualReview).delete()
        db.query(Transaction).delete()
        db.query(Policy).delete()
        db.commit()

        default_policy = Policy(
            max_attempts=2,
            max_discount=0,
            high_value_threshold=25000,
            manual_approval_threshold=25000,
            contact_start_time="09:00",
            contact_end_time="21:00",
            enabled=True,
        )
        db.add(default_policy)

        all_txns, recovered_cohort = generate_transactions()
        for txn in all_txns:
            db.add(txn)
        db.flush()  # assign ids without ending the transaction, so RecoveryEvent FKs below are valid

        # Seed a real recovery-pipeline audit trail for the "already
        # recovered" cohort, matching what recovery_service.py would have
        # written had these gone through analyze -> execute for real.
        # This is what makes recovered_revenue non-zero out of the box.
        for txn in recovered_cohort:
            action = "RETRY"
            idempotency_key = make_idempotency_key(txn, action)
            db.add(RecoveryEvent(
                transaction_id=txn.id,
                event_type="ACTION_EXECUTED",
                action=action,
                reason=f"{SIMULATED_TAG} Retry submitted",
                policy_result="ALLOWED",
                outcome="SUCCESS",
                idempotency_key=idempotency_key,
            ))
            db.add(RecoveryEvent(
                transaction_id=txn.id,
                event_type="PAYMENT_RECOVERED",
                action=action,
                outcome="RECOVERED",
                recovered_amount=txn.amount,
            ))

        db.commit()
        count = db.query(Transaction).count()
        recovered_total = sum(t.amount for t in recovered_cohort)
        print(f"Seeded {count} transactions, 1 default policy, and {len(recovered_cohort)} "
              f"recovered-pipeline events (₹{recovered_total:,.0f} recovered revenue).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()