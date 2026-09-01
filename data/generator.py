"""Synthetic data generator for realistic Indian payment failure transactions."""

import random
import uuid
from datetime import datetime, timedelta
from typing import List

from schemas.transaction import (
    Transaction,
    TransactionBatch,
    TransactionStatus,
    FailureCategory,
    PaymentMethod,
    CustomerSegment,
)

# Realistic Indian data pools
INDIAN_BANKS = ["HDFC", "SBI", "ICICI", "AXIS", "KOTAK", "YES", "PNB", "BOB", "CANARA", "UNION"]
UPI_PSPS = ["PHONEPE", "GPAY", "PAYTM", "CRED", "BHIM"]

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
    "Ananya", "Diya", "Myra", "Sara", "Aadhya", "Isha", "Kiara", "Riya", "Priya", "Neha",
    "Rohan", "Karan", "Rahul", "Amit", "Vijay", "Deepak", "Suresh", "Rajesh", "Pooja", "Sneha",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Joshi", "Mehta", "Shah", "Reddy",
    "Nair", "Iyer", "Rao", "Das", "Chatterjee", "Banerjee", "Mishra", "Pandey", "Tiwari", "Yadav",
]

FAILURE_CONFIG = [
    (FailureCategory.TRANSIENT_DOWNTIME, 0.35, ["bank_network_timeout", "psp_unavailable", "payment_timed_out", "gateway_error"]),
    (FailureCategory.INSUFFICIENT_FUNDS, 0.25, ["insufficient_funds"]),
    (FailureCategory.USER_DROPOUT, 0.20, ["user_cancelled", "otp_expired", "payment_timed_out"]),
    (FailureCategory.MANDATE_ISSUE, 0.10, ["mandate_not_found", "mandate_expired", "mandate_cancelled"]),
    (FailureCategory.LIMIT_EXCEEDED, 0.06, ["daily_limit_exceeded", "per_transaction_limit_exceeded"]),
    (FailureCategory.FATAL_DECLINE, 0.04, ["card_blocked", "fraud_suspected", "account_frozen", "card_expired", "stolen_card"]),
]

ERROR_SOURCE_MAP = {
    FailureCategory.TRANSIENT_DOWNTIME: "gateway",
    FailureCategory.INSUFFICIENT_FUNDS: "customer",
    FailureCategory.USER_DROPOUT: "customer",
    FailureCategory.MANDATE_ISSUE: "customer",
    FailureCategory.LIMIT_EXCEEDED: "customer",
    FailureCategory.FATAL_DECLINE: "customer",
}

ERROR_STEP_MAP = {
    FailureCategory.TRANSIENT_DOWNTIME: "payment_authorization",
    FailureCategory.INSUFFICIENT_FUNDS: "payment_authorization",
    FailureCategory.USER_DROPOUT: "payment_authentication",
    FailureCategory.MANDATE_ISSUE: "payment_initiation",
    FailureCategory.LIMIT_EXCEEDED: "payment_authorization",
    FailureCategory.FATAL_DECLINE: "payment_authorization",
}

ERROR_DESCRIPTIONS = {
    "bank_network_timeout": "The bank server did not respond in time",
    "psp_unavailable": "Payment service provider is temporarily unavailable",
    "payment_timed_out": "Payment processing timed out",
    "gateway_error": "Payment gateway encountered an internal error",
    "insufficient_funds": "Customer account has insufficient funds for this transaction",
    "user_cancelled": "Customer cancelled the payment",
    "otp_expired": "OTP verification timed out before customer could complete",
    "mandate_not_found": "No active mandate found for this subscription",
    "mandate_expired": "The payment mandate has expired",
    "mandate_cancelled": "Customer revoked the payment mandate",
    "daily_limit_exceeded": "Customer has exceeded daily transaction limit",
    "per_transaction_limit_exceeded": "Transaction amount exceeds per-transaction limit",
    "card_blocked": "Card has been blocked by the issuing bank",
    "fraud_suspected": "Transaction flagged for suspected fraud",
    "account_frozen": "Customer bank account is frozen",
    "card_expired": "Card has expired",
    "stolen_card": "Card reported as lost or stolen",
}

PAYMENT_METHODS_BY_CATEGORY = {
    FailureCategory.TRANSIENT_DOWNTIME: [PaymentMethod.UPI_INTENT, PaymentMethod.UPI_COLLECT, PaymentMethod.NETBANKING, PaymentMethod.CREDIT_CARD],
    FailureCategory.INSUFFICIENT_FUNDS: [PaymentMethod.DEBIT_CARD, PaymentMethod.UPI_INTENT, PaymentMethod.NETBANKING],
    FailureCategory.USER_DROPOUT: [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD, PaymentMethod.UPI_COLLECT, PaymentMethod.NETBANKING],
    FailureCategory.MANDATE_ISSUE: [PaymentMethod.UPI_AUTOPAY, PaymentMethod.E_NACH],
    FailureCategory.LIMIT_EXCEEDED: [PaymentMethod.UPI_INTENT, PaymentMethod.DEBIT_CARD],
    FailureCategory.FATAL_DECLINE: [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD],
}

BUSINESS_MODELS = ["SaaS", "E_COMMERCE", "SUBSCRIPTION", "LENDING"]


def _pick_category(rand: random.Random) -> tuple[FailureCategory, str]:
    """Pick a failure category based on realistic distribution."""
    r = rand.random()
    cumulative = 0.0
    for cat, prob, reasons in FAILURE_CONFIG:
        cumulative += prob
        if r <= cumulative:
            return cat, rand.choice(reasons)
    return FailureCategory.TRANSIENT_DOWNTIME, "bank_network_timeout"


def _pick_segment(ltv: float) -> CustomerSegment:
    """Assign customer segment based on LTV."""
    if ltv >= 100000:
        return CustomerSegment.VIP
    elif ltv >= 30000:
        return CustomerSegment.HIGH_VALUE
    elif ltv >= 5000:
        return CustomerSegment.STANDARD
    else:
        return CustomerSegment.CHURN_RISK


def generate_batch(count: int = 500, seed: int = 42) -> List[Transaction]:
    """Generate a batch of realistic synthetic failed payment transactions."""
    rand = random.Random(seed)
    transactions: List[Transaction] = []

    for i in range(count):
        # Failure category & reason
        category, reason = _pick_category(rand)
        error_code = f"BAD_REQUEST_ERROR"
        if category == FailureCategory.TRANSIENT_DOWNTIME:
            error_code = "GATEWAY_ERROR"

        # Amount distribution: 80% small, 15% medium, 5% high
        amount_r = rand.random()
        if amount_r < 0.80:
            amount = round(rand.uniform(99, 5000), 2)
        elif amount_r < 0.95:
            amount = round(rand.uniform(5000, 25000), 2)
        else:
            amount = round(rand.uniform(25000, 100000), 2)

        # Customer
        first = rand.choice(FIRST_NAMES)
        last = rand.choice(LAST_NAMES)
        customer_name = f"{first} {last}"
        cust_id = f"cust_{uuid.UUID(int=rand.getrandbits(128)).hex[:12]}"
        tx_id = f"txn_{uuid.UUID(int=rand.getrandbits(128)).hex[:14]}"
        order_id = f"order_{uuid.UUID(int=rand.getrandbits(128)).hex[:12]}"
        email = f"{first.lower()}.{last.lower()}@{'gmail.com' if rand.random() > 0.3 else 'yahoo.com'}"
        phone = f"+919{rand.randint(100000000, 999999999)}"

        # Payment details
        bank = rand.choice(INDIAN_BANKS)
        payment_method = rand.choice(PAYMENT_METHODS_BY_CATEGORY[category])
        psp = rand.choice(UPI_PSPS) if payment_method.value.startswith("UPI") else None

        # Timestamps — more failures during peak hours (7-10 PM IST)
        now = datetime.utcnow()
        if rand.random() < 0.4:
            hour = rand.randint(13, 16)  # 7-10 PM IST = 13:30-16:30 UTC
        else:
            hour = rand.randint(0, 23)
        minute = rand.randint(0, 59)
        created_at = now - timedelta(days=rand.randint(0, 7), hours=rand.randint(0, 5))
        created_at = created_at.replace(hour=hour, minute=minute, second=rand.randint(0, 59))

        # Customer context
        ltv = round(rand.uniform(500, 200000), 2)
        segment = _pick_segment(ltv)
        churn_risk = round(min(1.0, rand.random() * 0.6 + (0.4 if category == FailureCategory.FATAL_DECLINE else 0)), 3)
        hist_recovery = round(rand.uniform(0.2, 0.8), 3)
        salary_day = rand.choice([1, 1, 5, 5, 7, 10, 15, 25, None])
        prev_failures = rand.choices([0, 1, 2, 3, 4, 5], weights=[30, 25, 20, 12, 8, 5])[0]
        channel = rand.choice(["WHATSAPP", "WHATSAPP", "WHATSAPP", "SMS", "EMAIL", "IN_APP"])

        # Business context
        business_model = rand.choice(BUSINESS_MODELS)
        is_recurring = category == FailureCategory.MANDATE_ISSUE or (rand.random() < 0.3)
        sub_id = f"sub_{uuid.UUID(int=rand.getrandbits(128)).hex[:12]}" if is_recurring else None

        tx = Transaction(
            transaction_id=tx_id,
            order_id=order_id,
            customer_id=cust_id,
            customer_name=customer_name,
            customer_email=email,
            customer_phone=phone,
            customer_segment=segment,
            amount_inr=amount,
            currency="INR",
            payment_method=payment_method,
            issuer_bank=bank,
            psp=psp,
            error_code=error_code,
            error_source=ERROR_SOURCE_MAP[category],
            error_step=ERROR_STEP_MAP[category],
            error_reason=reason,
            error_description=ERROR_DESCRIPTIONS.get(reason, f"Payment failed: {reason}"),
            failure_category=category,
            attempt_count=rand.choices([1, 1, 1, 2, 2, 3], weights=[40, 20, 10, 15, 10, 5])[0],
            status=TransactionStatus.FAILED,
            created_at=created_at,
            failed_at=created_at,
            customer_ltv_inr=ltv,
            historical_recovery_rate=hist_recovery,
            churn_risk_score=churn_risk,
            preferred_channel=channel,
            salary_day_estimate=salary_day,
            previous_failures_30d=prev_failures,
            business_model=business_model,
            is_recurring=is_recurring,
            subscription_id=sub_id,
        )
        transactions.append(tx)

    return transactions


def generate_batch_with_metadata(count: int = 500, seed: int = 42) -> TransactionBatch:
    """Generate a batch with metadata."""
    transactions = generate_batch(count, seed)
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    total_amount = sum(t.amount_inr for t in transactions)
    return TransactionBatch(
        transactions=transactions,
        batch_id=batch_id,
        total_count=len(transactions),
        total_amount_inr=round(total_amount, 2),
    )
