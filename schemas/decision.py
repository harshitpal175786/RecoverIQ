from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class RecoveryAction(str, Enum):
    RETRY = "RETRY"
    PAYMENT_LINK = "PAYMENT_LINK"
    ALTERNATE_METHOD = "ALTERNATE_METHOD"
    DELAY_AND_RETRY = "DELAY_AND_RETRY"
    NO_ACTION = "NO_ACTION"
    ESCALATE = "ESCALATE"

class AgentDecision(BaseModel):
    """The AI agent's recommended recovery decision."""
    transaction_id: str
    root_cause_analysis: str = Field(..., description="Brief analysis of why payment failed")
    recommended_action: RecoveryAction
    retry_delay_minutes: int = Field(0, ge=0, description="Minutes to wait before action")
    alternate_payment_method: Optional[str] = Field(None)
    communication_channel: Optional[str] = Field(None, description="WHATSAPP | SMS | EMAIL | NONE")
    notification_message: Optional[str] = Field(None, description="Customer-facing message")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    risk_assessment: str = Field(..., description="Low | Medium | High")
    reasoning: str = Field(..., description="Full chain-of-thought reasoning")
    
    ai_model_used: Optional[str] = Field(None, description="Model that generated this decision")
    is_fallback: bool = Field(False, description="True if deterministic fallback was used")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GuardrailResult(BaseModel):
    """Result of guardrail checks on an agent decision."""
    passed: bool
    checks_applied: list[str] = Field(default_factory=list)
    checks_blocked: list[str] = Field(default_factory=list)
    original_action: RecoveryAction
    final_action: RecoveryAction
    modifications: list[str] = Field(default_factory=list, description="What guardrails changed")

class RecoveryAttempt(BaseModel):
    """Records a single recovery attempt and its outcome."""
    attempt_id: str
    transaction_id: str
    action: RecoveryAction
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = False
    outcome_details: str = ""
    amount_recovered_inr: float = 0.0
    verification_status: str = Field("PENDING", description="PENDING | VERIFIED_SUCCESS | VERIFIED_FAILED | TIMEOUT")
    verified_at: Optional[datetime] = None
