from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_ref = Column(String, unique=True, index=True)  # e.g. TXN-10482
    customer_id = Column(String, index=True)
    gateway = Column(String, default="razorpay")
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    status = Column(String, default="FAILED")  # FAILED, SUCCESS, ABANDONED
    failure_code = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)
    attempt_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_attempt_at = Column(DateTime, default=datetime.utcnow)
    customer_previous_successes = Column(Integer, default=0)
    recovery_status = Column(String, default="UNRESOLVED")
    # UNRESOLVED, ELIGIBLE, ACTION_TAKEN, RECOVERED, STOPPED, MANUAL_REVIEW

    recovery_events = relationship("RecoveryEvent", back_populates="transaction")
    manual_reviews = relationship("ManualReview", back_populates="transaction")


class RecoveryEvent(Base):
    __tablename__ = "recovery_events"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    event_type = Column(String)  # TRANSACTION_DETECTED, AI_RECOMMENDATION, etc.
    action = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    policy_result = Column(String, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)
    outcome = Column(String, nullable=True)
    recovered_amount = Column(Float, default=0)
    idempotency_key = Column(String, index=True, nullable=True)

    transaction = relationship("Transaction", back_populates="recovery_events")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    max_attempts = Column(Integer, default=2)
    max_discount = Column(Float, default=0)
    high_value_threshold = Column(Float, default=25000)
    manual_approval_threshold = Column(Float, default=25000)
    contact_start_time = Column(String, default="09:00")
    contact_end_time = Column(String, default="21:00")
    enabled = Column(Boolean, default=True)


class ManualReview(Base):
    __tablename__ = "manual_reviews"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    reason = Column(String)
    recommendation = Column(String, nullable=True)
    status = Column(String, default="AWAITING_MERCHANT_APPROVAL")
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    transaction = relationship("Transaction", back_populates="manual_reviews")