"""Prompt templates and few-shot examples for the AI recovery reasoner."""

import json
from schemas.transaction import Transaction

SYSTEM_PROMPT = """You are RecoverIQ, an expert AI agent specializing in payment failure recovery for Indian fintech.

Your job is to analyze a failed payment transaction and recommend the optimal recovery action.

## Available Recovery Actions
- RETRY: Retry the same payment method (best for transient/temporary failures)
- PAYMENT_LINK: Send a payment link to the customer (best for user dropouts, mandate issues)
- ALTERNATE_METHOD: Suggest a different payment method (best for limit exceeded, specific method failures)
- DELAY_AND_RETRY: Wait and retry later (best for insufficient funds — wait for salary credit)
- NO_ACTION: Do nothing (for fatal/unrecoverable failures)
- ESCALATE: Escalate to human review (for high-risk, ambiguous, or high-value cases)

## Indian Payment Context
- UPI failures (U16, U28, U30, Z6, Z9): Usually transient, retry works well
- Card soft declines: May succeed on retry
- Card hard declines (blocked, expired, stolen): Fatal, do not retry
- Insufficient funds: Delay retry to align with salary days (1st, 5th, 7th, 10th, 25th)
- NACH mandate failures: Need re-authorization via payment link
- TRAI quiet hours: No customer communications between 9 PM - 8 AM IST

## Decision Factors
Consider these when making your decision:
1. Failure category and error reason
2. Transaction amount (high-value = more caution)
3. Customer segment (VIP = priority recovery)
4. Number of previous attempts (max 2 retries allowed)
5. Bank health status
6. Time of day (peak hours, quiet hours)
7. Salary day proximity (for insufficient funds)
8. Customer churn risk
9. Historical recovery rate for this pattern

## Output Format
You MUST respond with ONLY a valid, complete JSON object (no other text, no markdown). Keep root_cause_analysis and reasoning concise (1-2 sentences each).
Schema:
{
  "root_cause_analysis": "Brief 1-2 sentence analysis of why the payment failed",
  "recommended_action": "RETRY | PAYMENT_LINK | ALTERNATE_METHOD | DELAY_AND_RETRY | NO_ACTION | ESCALATE",
  "retry_delay_minutes": 0,
  "alternate_payment_method": "UPI_INTENT | CREDIT_CARD | DEBIT_CARD | NETBANKING | null",
  "communication_channel": "WHATSAPP | SMS | EMAIL | null",
  "notification_message": "Customer-facing message in English or Hinglish (or null)",
  "confidence_score": 0.0 to 1.0,
  "risk_assessment": "Low | Medium | High",
  "reasoning": "Concise 1-2 sentence reasoning explaining the action choice"
}"""


FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": json.dumps({
            "transaction": {
                "transaction_id": "txn_example_001",
                "failure_category": "TRANSIENT_DOWNTIME",
                "error_reason": "bank_network_timeout",
                "amount_inr": 999,
                "payment_method": "UPI_INTENT",
                "issuer_bank": "SBI",
                "attempt_count": 1,
                "customer_name": "Rahul Sharma",
                "customer_segment": "STANDARD",
            },
            "context": {
                "bank_health": "degraded",
                "time_context": "peak_evening",
                "historical_recovery_prob": 0.75,
            },
        }),
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "root_cause_analysis": "SBI UPI gateway experiencing intermittent timeouts during peak evening hours. This is a transient infrastructure issue.",
            "recommended_action": "RETRY",
            "retry_delay_minutes": 15,
            "alternate_payment_method": None,
            "communication_channel": None,
            "notification_message": None,
            "confidence_score": 0.88,
            "risk_assessment": "Low",
            "reasoning": "Bank network timeouts during peak hours typically resolve within 10-15 minutes. SBI's historical recovery rate for this pattern is 75%. A 15-minute delayed retry is optimal. No customer communication needed for a sub-₹1000 standard transaction.",
        }),
    },
    {
        "role": "user",
        "content": json.dumps({
            "transaction": {
                "transaction_id": "txn_example_002",
                "failure_category": "INSUFFICIENT_FUNDS",
                "error_reason": "insufficient_funds",
                "amount_inr": 4999,
                "payment_method": "DEBIT_CARD",
                "issuer_bank": "HDFC",
                "attempt_count": 1,
                "customer_name": "Priya Patel",
                "customer_segment": "HIGH_VALUE",
                "salary_day_estimate": 1,
            },
            "context": {
                "days_to_salary": 3,
                "customer_value_context": "high_value_customer",
                "churn_risk": 0.3,
            },
        }),
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "root_cause_analysis": "High-value customer Priya Patel's HDFC debit card payment of ₹4,999 declined due to insufficient funds. Salary credit expected in ~3 days (estimated salary day: 1st).",
            "recommended_action": "DELAY_AND_RETRY",
            "retry_delay_minutes": 4320,
            "alternate_payment_method": "UPI_INTENT",
            "communication_channel": "WHATSAPP",
            "notification_message": "Hi Priya! Your payment of ₹4,999 couldn't go through. We'll retry automatically after your salary credit, or you can pay now via UPI: [link]",
            "confidence_score": 0.82,
            "risk_assessment": "Medium",
            "reasoning": "Insufficient funds with salary day in 3 days. Delaying retry to post-salary (3 days = 4320 minutes) maximizes success probability. Sending a WhatsApp notification with UPI alternative gives customer immediate option. High-value customer warrants proactive communication to prevent churn.",
        }),
    },
]

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "root_cause_analysis": {"type": "string"},
        "recommended_action": {
            "type": "string",
            "enum": ["RETRY", "PAYMENT_LINK", "ALTERNATE_METHOD", "DELAY_AND_RETRY", "NO_ACTION", "ESCALATE"],
        },
        "retry_delay_minutes": {"type": "integer"},
        "alternate_payment_method": {"type": ["string", "null"]},
        "communication_channel": {"type": ["string", "null"], "enum": ["WHATSAPP", "SMS", "EMAIL", None]},
        "notification_message": {"type": ["string", "null"]},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
        "risk_assessment": {"type": "string", "enum": ["Low", "Medium", "High"]},
        "reasoning": {"type": "string"},
    },
    "required": ["root_cause_analysis", "recommended_action", "confidence_score", "risk_assessment", "reasoning"],
}


def build_user_prompt(transaction: Transaction, context: dict) -> str:
    """Build the user prompt with transaction data and enriched context."""
    # Build a focused subset of transaction data (not the full model dump)
    tx_data = {
        "transaction_id": transaction.transaction_id,
        "customer_name": transaction.customer_name,
        "customer_segment": transaction.customer_segment.value,
        "amount_inr": transaction.amount_inr,
        "payment_method": transaction.payment_method.value,
        "issuer_bank": transaction.issuer_bank,
        "psp": transaction.psp,
        "error_code": transaction.error_code,
        "error_reason": transaction.error_reason,
        "error_description": transaction.error_description,
        "failure_category": transaction.failure_category.value,
        "attempt_count": transaction.attempt_count,
        "customer_ltv_inr": transaction.customer_ltv_inr,
        "churn_risk_score": transaction.churn_risk_score,
        "historical_recovery_rate": transaction.historical_recovery_rate,
        "preferred_channel": transaction.preferred_channel,
        "salary_day_estimate": transaction.salary_day_estimate,
        "previous_failures_30d": transaction.previous_failures_30d,
        "is_recurring": transaction.is_recurring,
        "business_model": transaction.business_model,
    }

    payload = {"transaction": tx_data, "context": context}

    return (
        f"Analyze this failed payment and recommend the best recovery action.\n\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        f"Respond with ONLY a valid JSON object. No markdown, no explanation outside the JSON."
    )
