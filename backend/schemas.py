from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---------- Transaction ----------

class TransactionOut(BaseModel):
    id: int
    transaction_ref: str
    customer_id: str
    gateway: str
    amount: float
    currency: str
    status: str
    failure_code: Optional[str]
    failure_reason: Optional[str]
    attempt_count: int
    created_at: datetime
    last_attempt_at: datetime
    customer_previous_successes: int
    recovery_status: str

    class Config:
        from_attributes = True


# ---------- Recovery Score ----------

class RecoveryScoreOut(BaseModel):
    score: int
    label: str  # e.g. HIGH PRIORITY, LOW PRIORITY, NOT ELIGIBLE
    factors: List[str]


# ---------- Recommendation ----------

class RecommendationOut(BaseModel):
    recommended_action: str
    reasoning: str
    evidence: List[str]
    ai_explanation: Optional[str] = None
    disallowed_component: Optional[str] = None  # e.g. "10% discount" (for demo)


# ---------- Policy evaluation ----------

class PolicyDecisionOut(BaseModel):
    decision: str  # ALLOWED, BLOCKED, MANUAL_REVIEW
    reason: str
    alternative_action: Optional[str] = None


# ---------- Full analyze response ----------

class AnalyzeResponse(BaseModel):
    transaction_id: str
    recovery_score: RecoveryScoreOut
    recommendation: RecommendationOut
    policy_decision: PolicyDecisionOut
    environment: str = "SIMULATED_TEST"


# ---------- Execute response ----------

class ExecuteResponse(BaseModel):
    transaction_id: str
    status: str  # EXECUTED, DUPLICATE_PREVENTED, FAILED, AWAITING_APPROVAL
    action: Optional[str] = None
    outcome: Optional[str] = None
    recovered_amount: Optional[float] = None
    message: Optional[str] = None
    idempotency_key: Optional[str] = None


# ---------- Policy ----------

class PolicyOut(BaseModel):
    id: int
    max_attempts: int
    max_discount: float
    high_value_threshold: float
    manual_approval_threshold: float
    contact_start_time: str
    contact_end_time: str
    enabled: bool

    class Config:
        from_attributes = True


class PolicyUpdate(BaseModel):
    max_attempts: Optional[int] = None
    max_discount: Optional[float] = None
    high_value_threshold: Optional[float] = None
    manual_approval_threshold: Optional[float] = None
    contact_start_time: Optional[str] = None
    contact_end_time: Optional[str] = None
    enabled: Optional[bool] = None


# ---------- Manual review ----------

class ManualReviewOut(BaseModel):
    id: int
    transaction_id: int
    reason: str
    recommendation: Optional[str]
    status: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------- Audit ----------

class AuditEventOut(BaseModel):
    id: int
    transaction_id: int
    event_type: str
    action: Optional[str]
    reason: Optional[str]
    policy_result: Optional[str]
    executed_at: datetime
    outcome: Optional[str]
    recovered_amount: Optional[float]

    class Config:
        from_attributes = True


# ---------- Dashboard ----------

class DashboardOut(BaseModel):
    transactions_analyzed: int
    revenue_at_risk: float
    eligible_cases: int
    actions_executed: int
    successful_recoveries: int
    recovered_revenue: float
    environment: str = "SIMULATED_TEST"