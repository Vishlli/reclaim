import pytest
from datetime import datetime

from database import Base, engine, SessionLocal
from models import Transaction, Policy, RecoveryEvent, ManualReview


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    default_policy = Policy(
        max_attempts=2,
        max_discount=0,
        high_value_threshold=25000,
        manual_approval_threshold=25000,
        contact_start_time="00:00",
        contact_end_time="23:59",
        enabled=True,
    )
    session.add(default_policy)
    session.commit()

    yield session

    session.close()


def make_transaction(
    session,
    ref="TXN-TEST",
    amount=5000,
    status="FAILED",
    failure_code="payment_timeout",
    attempts=1,
    prev_success=0,
    recovery_status="UNRESOLVED",
):
    txn = Transaction(
        transaction_ref=ref,
        customer_id="Customer Test",
        gateway="razorpay",
        amount=amount,
        currency="INR",
        status=status,
        failure_code=failure_code,
        failure_reason="test",
        attempt_count=attempts,
        created_at=datetime.utcnow(),
        last_attempt_at=datetime.utcnow(),
        customer_previous_successes=prev_success,
        recovery_status=recovery_status,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn