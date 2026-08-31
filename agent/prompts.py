import json
from schemas.transaction import Transaction

SYSTEM_PROMPT = """You are an AI recovery agent for a payment gateway. Your goal is to analyze payment failures and recommend the best recovery action.
You must return a valid JSON object matching the required schema. No other text should be output.

Analyze the root cause, determine the best action, and provide communication details if necessary.
Consider the provided context (bank health, time of day, customer value, etc.) carefully.
"""

FEW_SHOT_EXAMPLES = [
    {
        "input": {
            "transaction_id": "txn_123",
            "failure_category": "TRANSIENT_DOWNTIME",
            "amount": 1000
        },
        "output": {
            "root_cause_analysis": "Temporary bank downtime detected.",
            "recommended_action": "RETRY",
            "retry_delay_minutes": 15,
            "alternate_payment_method": None,
            "communication_channel": "NONE",
            "notification_message": None,
            "confidence_score": 0.9,
            "risk_assessment": "Low risk, standard retry.",
            "reasoning": "Downtimes usually resolve quickly. A retry in 15 mins is optimal."
        }
    },
    {
        "input": {
            "transaction_id": "txn_456",
            "failure_category": "INSUFFICIENT_FUNDS",
            "amount": 5000
        },
        "output": {
            "root_cause_analysis": "Customer has insufficient funds in their primary account.",
            "recommended_action": "DELAY_AND_RETRY",
            "retry_delay_minutes": 1440,
            "alternate_payment_method": "UPI",
            "communication_channel": "WHATSAPP",
            "notification_message": "Hi, your recent payment of 5000 failed. Please ensure sufficient balance or try using UPI.",
            "confidence_score": 0.8,
            "risk_assessment": "Medium risk, requires customer action.",
            "reasoning": "Retrying immediately will fail. Delaying and notifying the customer to use another method is best."
        }
    }
]

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "root_cause_analysis": {"type": "string"},
        "recommended_action": {"type": "string", "enum": ["RETRY", "PAYMENT_LINK", "ALTERNATE_METHOD", "DELAY_AND_RETRY", "NO_ACTION", "ESCALATE"]},
        "retry_delay_minutes": {"type": "integer", "nullable": True},
        "alternate_payment_method": {"type": "string", "nullable": True},
        "communication_channel": {"type": "string", "enum": ["NONE", "EMAIL", "SMS", "WHATSAPP"]},
        "notification_message": {"type": "string", "nullable": True},
        "confidence_score": {"type": "number"},
        "risk_assessment": {"type": "string"},
        "reasoning": {"type": "string"}
    },
    "required": ["root_cause_analysis", "recommended_action", "confidence_score", "risk_assessment", "reasoning"]
}

def build_user_prompt(transaction: Transaction, context: dict) -> str:
    data = {
        "transaction": transaction.model_dump(mode="json"),
        "context": context
    }
    return f"Analyze the following transaction and context:\n{json.dumps(data, indent=2)}\n\nOutput only a JSON object matching the schema."
