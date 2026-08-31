from pydantic import BaseModel, Field
from datetime import datetime

class RecoveryMetrics(BaseModel):
    """Metrics from a recovery batch run."""
    batch_id: str
    strategy: str = Field(..., description="BASELINE | RECOVERIQ")
    
    total_transactions: int = 0
    total_failed_amount_inr: float = 0.0
    
    recovered_count: int = 0
    recovered_amount_inr: float = 0.0
    recovery_rate_pct: float = 0.0
    
    escalated_count: int = 0
    escalation_rate_pct: float = 0.0
    
    no_action_count: int = 0
    actions_attempted: int = 0
    
    false_action_count: int = 0
    false_action_rate_pct: float = 0.0
    
    guardrail_blocks: int = 0
    guardrail_compliance_pct: float = 100.0
    
    verification_coverage_pct: float = 0.0
    
    avg_confidence_score: float = 0.0
    avg_recovery_time_minutes: float = 0.0
    
    action_distribution: dict[str, int] = Field(default_factory=dict)
    failure_category_distribution: dict[str, int] = Field(default_factory=dict)
    
    computed_at: datetime = Field(default_factory=datetime.utcnow)

class ComparisonReport(BaseModel):
    """Baseline vs RecoverIQ comparison."""
    baseline: RecoveryMetrics
    recoveriq: RecoveryMetrics
    
    recovery_rate_uplift_pct: float = 0.0
    revenue_uplift_inr: float = 0.0
    revenue_uplift_pct: float = 0.0
    
    false_action_improvement_pct: float = 0.0
    efficiency_improvement_pct: float = 0.0
    
    summary: str = ""
    computed_at: datetime = Field(default_factory=datetime.utcnow)
