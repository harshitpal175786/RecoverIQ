from datetime import datetime
from schemas.transaction import Transaction, TransactionStatus, FailureCategory
from schemas.decision import AgentDecision, RecoveryAction, GuardrailResult
from schemas.policy import MerchantPolicy
from config import get_settings

def enforce_guardrails(transaction: Transaction, decision: AgentDecision, policy: MerchantPolicy) -> GuardrailResult:
    """Apply all guardrails and return modified decision if needed."""
    settings = get_settings()
    passed = []
    blocked = []
    modified_action = decision.recommended_action
    
    # 1. Max 2 automated retries
    if transaction.attempt_count >= 2 and modified_action == RecoveryAction.RETRY:
        blocked.append("Max retries exceeded")
        modified_action = RecoveryAction.ESCALATE
    else:
        passed.append("Max retries check")

    # 3. High-value cap
    if transaction.amount > settings.HIGH_VALUE_THRESHOLD_INR and modified_action not in [RecoveryAction.NO_ACTION, RecoveryAction.ESCALATE]:
        blocked.append("High-value cap exceeded")
        modified_action = RecoveryAction.ESCALATE
    else:
        passed.append("High-value check")

    # 4. Unknown failure
    if transaction.failure_category == FailureCategory.UNKNOWN:
        blocked.append("Unknown failure auto-escalate")
        modified_action = RecoveryAction.ESCALATE
    else:
        passed.append("Known failure check")

    # 5. Already successful
    if transaction.status == TransactionStatus.RECOVERED:
        blocked.append("Already recovered")
        modified_action = RecoveryAction.NO_ACTION
    else:
        passed.append("Not yet recovered check")

    # 7. Allow-listed actions only
    if modified_action.value not in [a.value for a in policy.allowed_actions]:
        blocked.append("Action not allow-listed")
        modified_action = RecoveryAction.ESCALATE
    else:
        passed.append("Allow-listed action check")

    # 10. Recovery window
    if transaction.created_at:
        hours_since = (datetime.utcnow() - transaction.created_at).total_seconds() / 3600
        if hours_since > settings.RECOVERY_WINDOW_HOURS:
            blocked.append("Recovery window expired")
            modified_action = RecoveryAction.NO_ACTION
        else:
            passed.append("Recovery window check")
            
    # 11. Low confidence
    if decision.confidence_score < settings.LLM_CONFIDENCE_THRESHOLD:
        blocked.append("Low confidence score")
        modified_action = RecoveryAction.ESCALATE
    else:
        passed.append("Confidence check")
        
    # 12. Quiet hours
    current_hour = datetime.now().hour
    is_quiet_hour = current_hour >= settings.QUIET_HOURS_START or current_hour < settings.QUIET_HOURS_END
    if is_quiet_hour and decision.communication_channel != "NONE":
        blocked.append("Quiet hours communication delayed")
        # Could change to DELAY_AND_RETRY or NO_ACTION depending on strictness
        modified_action = RecoveryAction.DELAY_AND_RETRY
        decision.retry_delay_minutes = (24 - current_hour + settings.QUIET_HOURS_END) * 60
    else:
        passed.append("Quiet hours check")

    return GuardrailResult(
        passed_checks=passed,
        blocked_checks=blocked,
        modified_action=modified_action,
        original_action=decision.recommended_action
    )
