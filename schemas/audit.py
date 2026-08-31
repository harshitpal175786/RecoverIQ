from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Optional
from enum import Enum

class AuditStage(str, Enum):
    INGESTION = "INGESTION"
    RISK_DETECTION = "RISK_DETECTION"
    CONTEXT_BUILDING = "CONTEXT_BUILDING"
    AI_REASONING = "AI_REASONING"
    CANDIDATE_SCORING = "CANDIDATE_SCORING"
    GUARDRAIL_CHECK = "GUARDRAIL_CHECK"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"
    OUTCOME = "OUTCOME"

class AuditLog(BaseModel):
    """Complete audit trail entry for a recovery pipeline step."""
    log_id: str
    transaction_id: str
    batch_id: Optional[str] = None
    stage: AuditStage
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    
    ai_used: bool = False
    ai_model: Optional[str] = None
    ai_prompt: Optional[str] = None
    ai_raw_response: Optional[str] = None
    
    guardrails_applied: list[str] = Field(default_factory=list)
    guardrails_blocked: list[str] = Field(default_factory=list)
    
    duration_ms: float = 0.0
    error: Optional[str] = None
    outcome: str = Field("PENDING", description="SUCCESS | FAILED | BLOCKED | ESCALATED | SKIPPED")

class EscalationRecord(BaseModel):
    """Record of a transaction escalated to human review."""
    escalation_id: str
    transaction_id: str
    reason: str
    priority: str = Field("MEDIUM", description="LOW | MEDIUM | HIGH | CRITICAL")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
