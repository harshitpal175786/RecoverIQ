from pydantic import BaseModel, Field

class MerchantPolicy(BaseModel):
    """Merchant-specific recovery policy configuration."""
    merchant_id: str = "default"
    max_retries: int = Field(2, ge=0, le=5)
    cooldown_minutes: int = Field(5, ge=1)
    high_value_threshold_inr: float = Field(50000, gt=0)
    recovery_window_hours: int = Field(72, ge=1)
    quiet_hours_start: int = Field(21, ge=0, le=23)  # 9 PM
    quiet_hours_end: int = Field(8, ge=0, le=23)      # 8 AM
    allowed_actions: list[str] = Field(
        default_factory=lambda: ["RETRY", "PAYMENT_LINK", "ALTERNATE_METHOD", "DELAY_AND_RETRY", "NO_ACTION", "ESCALATE"]
    )
    auto_escalate_on_unknown: bool = True
    require_verification: bool = True
    llm_confidence_threshold: float = Field(0.6, ge=0.0, le=1.0)

class GuardrailConfig(BaseModel):
    """Global guardrail configuration."""
    max_retries_per_transaction: int = 2
    min_cooldown_minutes: int = 5
    high_value_auto_action_cap_inr: float = 50000
    escalate_on_unknown_failure: bool = True
    skip_already_successful: bool = True
    enforce_idempotency: bool = True
    allowed_actions: list[str] = Field(
        default_factory=lambda: ["RETRY", "PAYMENT_LINK", "ALTERNATE_METHOD", "DELAY_AND_RETRY", "NO_ACTION", "ESCALATE"]
    )
    require_json_schema_validation: bool = True
    verify_before_next_action: bool = True
    recovery_window_hours: int = 72
    llm_confidence_threshold: float = 0.6
    quiet_hours_start: int = 21
    quiet_hours_end: int = 8
