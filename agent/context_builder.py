from datetime import datetime
from schemas.transaction import Transaction, FailureCategory, CustomerSegment

def build_context(transaction: Transaction) -> dict:
    """Build enriched context dict for AI reasoning."""
    context = {}

    # Simulated bank health status
    # In a real app, this would query a real-time service
    if transaction.failure_category == FailureCategory.TRANSIENT_DOWNTIME:
        context["bank_health"] = "Degraded connectivity detected for the issuing bank."
    else:
        context["bank_health"] = "Normal operational status."

    # Time-of-day context
    current_hour = datetime.now().hour
    if 10 <= current_hour <= 14 or 18 <= current_hour <= 22:
        context["time_context"] = "Peak transaction hours."
    else:
        context["time_context"] = "Off-peak hours."
        
    current_day = datetime.now().day
    if 28 <= current_day <= 31 or 1 <= current_day <= 5:
        context["time_context"] += " Salary day proximity."

    # Customer value context
    if transaction.customer_segment == CustomerSegment.VIP:
        context["customer_value_context"] = "VIP customer, prioritize smooth experience and gentle communication."
    elif transaction.customer_segment == CustomerSegment.CHURN_RISK:
        context["customer_value_context"] = "High churn risk, offer alternatives proactively."
    else:
        context["customer_value_context"] = "Standard customer treatment."

    # Historical recovery probability
    recovery_probs = {
        FailureCategory.TRANSIENT_DOWNTIME: 0.85,
        FailureCategory.INSUFFICIENT_FUNDS: 0.40,
        FailureCategory.USER_DROPOUT: 0.60,
        FailureCategory.MANDATE_ISSUE: 0.50,
        FailureCategory.LIMIT_EXCEEDED: 0.30,
        FailureCategory.FATAL_DECLINE: 0.05
    }
    context["historical_recovery_prob"] = recovery_probs.get(transaction.failure_category, 0.50)

    # Recommended retry window
    if transaction.failure_category == FailureCategory.TRANSIENT_DOWNTIME:
        context["recommended_retry_window"] = "15-30 minutes"
    elif transaction.failure_category == FailureCategory.INSUFFICIENT_FUNDS:
        context["recommended_retry_window"] = "24 hours"
    else:
        context["recommended_retry_window"] = "Immediate to 1 hour"

    context["additional_signals"] = {
        "is_weekend": datetime.now().weekday() >= 5
    }

    return context
