from schemas.transaction import Transaction, FailureCategory
from schemas.decision import AgentDecision, RecoveryAction

def deterministic_decision(transaction: Transaction, context: dict) -> AgentDecision:
    """Pure rule-based decision making. No AI required."""
    
    if transaction.attempt_count >= 2:
        return AgentDecision(
            transaction_id=transaction.transaction_id,
            is_fallback=True,
            root_cause_analysis="Max retries reached.",
            recommended_action=RecoveryAction.ESCALATE,
            confidence_score=0.95,
            risk_assessment="High risk due to max retries.",
            reasoning="Cannot exceed maximum allowed retries."
        )

    cat = transaction.failure_category
    amount = transaction.amount_inr
    customer_name = getattr(transaction, 'customer_name', 'Customer')
    
    if cat == FailureCategory.TRANSIENT_DOWNTIME:
        return AgentDecision(
            transaction_id=transaction.transaction_id,
            is_fallback=True,
            root_cause_analysis="Transient network/bank downtime.",
            recommended_action=RecoveryAction.RETRY,
            retry_delay_minutes=15,
            confidence_score=0.85,
            risk_assessment="Low risk",
            reasoning="System issues usually resolve in a few minutes."
        )
    elif cat == FailureCategory.INSUFFICIENT_FUNDS:
        return AgentDecision(
            transaction_id=transaction.transaction_id,
            is_fallback=True,
            root_cause_analysis="Insufficient funds.",
            recommended_action=RecoveryAction.DELAY_AND_RETRY,
            retry_delay_minutes=1440,
            communication_channel="WHATSAPP",
            notification_message=f"Hi {customer_name}, your payment of INR {amount} failed. Please ensure sufficient funds or try another payment method.",
            confidence_score=0.75,
            risk_assessment="Medium risk",
            reasoning="Requires customer to add funds."
        )
    elif cat == FailureCategory.USER_DROPOUT:
        return AgentDecision(
            transaction_id=transaction.transaction_id,
            is_fallback=True,
            root_cause_analysis="User abandoned transaction.",
            recommended_action=RecoveryAction.PAYMENT_LINK,
            retry_delay_minutes=5,
            communication_channel="WHATSAPP",
            notification_message=f"Hi {customer_name}, it looks like you couldn't complete your payment of INR {amount}. Click here to complete it.",
            confidence_score=0.80,
            risk_assessment="Medium risk",
            reasoning="User might just need a nudge to complete."
        )
    elif cat == FailureCategory.MANDATE_ISSUE:
        return AgentDecision(
            transaction_id=transaction.transaction_id,
            is_fallback=True,
            root_cause_analysis="Mandate validation failed.",
            recommended_action=RecoveryAction.PAYMENT_LINK,
            communication_channel="EMAIL",
            confidence_score=0.70,
            risk_assessment="Medium risk",
            reasoning="Customer needs to re-authenticate the mandate."
        )
    elif cat == FailureCategory.LIMIT_EXCEEDED:
        return AgentDecision(
            transaction_id=transaction.transaction_id,
            is_fallback=True,
            root_cause_analysis="Transaction limit exceeded.",
            recommended_action=RecoveryAction.ALTERNATE_METHOD,
            communication_channel="WHATSAPP",
            notification_message=f"Hi {customer_name}, your payment of INR {amount} exceeded limits. Please try a different payment method.",
            confidence_score=0.80,
            risk_assessment="Medium risk",
            reasoning="Different method or account required."
        )
    elif cat == FailureCategory.FATAL_DECLINE:
        action = RecoveryAction.ESCALATE if amount > 50000 else RecoveryAction.NO_ACTION
        return AgentDecision(
            transaction_id=transaction.transaction_id,
            is_fallback=True,
            root_cause_analysis="Fatal decline by issuer.",
            recommended_action=action,
            confidence_score=0.90,
            risk_assessment="High risk",
            reasoning="Cannot recover without manual intervention."
        )
    
    # Default fallback
    return AgentDecision(
            transaction_id=transaction.transaction_id,
            is_fallback=True,
        root_cause_analysis="Unknown failure.",
        recommended_action=RecoveryAction.ESCALATE,
        confidence_score=1.0,
        risk_assessment="Unknown risk",
        reasoning="Escalating due to unmapped failure category."
    )
