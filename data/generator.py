import random
import uuid
from datetime import datetime, timedelta
from typing import List

from schemas.transaction import (
    Transaction, 
    TransactionStatus, 
    FailureCategory
)

# Realistic Indian data pool
INDIAN_BANKS = ["HDFC", "SBI", "ICICI", "AXIS", "KOTAK", "YES", "PNB", "BOB", "CANARA", "UNION"]
UPI_PSPS = ["PHONEPE", "GPAY", "PAYTM", "CRED", "BHIM"]

FAILURE_CATEGORIES = [
    (FailureCategory.TRANSIENT_DOWNTIME, 0.35, ["bank_network_timeout", "psp_unavailable"]),
    (FailureCategory.INSUFFICIENT_FUNDS, 0.25, ["insufficient_funds"]),
    (FailureCategory.USER_DROPOUT, 0.20, ["user_cancelled", "timeout"]),
    (FailureCategory.MANDATE_ISSUE, 0.10, ["mandate_not_found", "mandate_expired"]),
    (FailureCategory.LIMIT_EXCEEDED, 0.06, ["daily_limit_exceeded", "per_transaction_limit_exceeded"]),
    (FailureCategory.FATAL_DECLINE, 0.04, ["card_blocked", "fraud_suspected", "account_frozen"])
]

def generate_batch(count: int = 500, seed: int = 42) -> List[Transaction]:
    rand = random.Random(seed)
    transactions = []
    
    for i in range(count):
        # Determine failure category
        r = rand.random()
        cumulative = 0
        cat, reasons = None, []
        for c, prob, r_list in FAILURE_CATEGORIES:
            cumulative += prob
            if r <= cumulative:
                cat = c
                reasons = r_list
                break
        
        if cat is None:
            cat = FailureCategory.TRANSIENT_DOWNTIME
            reasons = ["bank_network_timeout"]

        reason = rand.choice(reasons)
        error_code = f"ERR_{reason.upper()}"
        
        # Amount distribution
        amount_r = rand.random()
        if amount_r < 0.80:
            amount = round(rand.uniform(99, 5000), 2)
        elif amount_r < 0.95:
            amount = round(rand.uniform(5000, 25000), 2)
        else:
            amount = round(rand.uniform(25000, 100000), 2)
            
        bank = rand.choice(INDIAN_BANKS)
        upi = rand.choice(UPI_PSPS) if rand.random() > 0.4 else None
        
        # Dates and Times
        now = datetime.utcnow()
        # More failures during peak hours (19:00 to 22:00)
        if rand.random() < 0.4:
            hour = rand.randint(19, 21)
        else:
            hour = rand.randint(0, 23)
        minute = rand.randint(0, 59)
        created_at = now - timedelta(days=rand.randint(0, 30))
        created_at = created_at.replace(hour=hour, minute=minute)
        
        # Risk & Segments
        churn_risk = min(1.0, rand.random() * 0.5 + (0.5 if cat == FailureCategory.FATAL_DECLINE else 0))
        segment = rand.choice(["high_ltv", "mid_ltv", "low_ltv"])
        salary_day = rand.choice([1, 5, 7, 10, None])
        
        tx_id = f"txn_{uuid.UUID(int=rand.getrandbits(128)).hex[:14]}"
        cust_id = f"cust_{uuid.UUID(int=rand.getrandbits(128)).hex[:14]}"
        
        tx = Transaction(
            id=tx_id,
            customer_id=cust_id,
            amount=amount,
            currency="INR",
            status=TransactionStatus.FAILED,
            failure_category=cat,
            failure_reason=reason,
            error_code=error_code,
            bank_name=bank,
            upi_psp=upi,
            created_at=created_at,
            customer_segment=segment,
            churn_risk_score=churn_risk,
            salary_day_estimate=salary_day
        )
        transactions.append(tx)
        
    return transactions
