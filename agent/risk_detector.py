from schemas.transaction import Transaction, FailureCategory, TransactionStatus, CustomerSegment

# In-memory store for deduplication
_processed_transactions = set()

def detect_risk(transaction: Transaction) -> tuple[bool, float, str]:
    """Returns (is_fatal, risk_score, risk_reason)"""
    if transaction.failure_category == FailureCategory.FATAL_DECLINE:
        return True, 1.0, "Transaction failed with FATAL_DECLINE."
    
    risk_score = 0.0
    reasons = []

    # Amount-based risk
    if transaction.amount_inr > 50000:
        risk_score += 0.4
        reasons.append("High transaction amount")
    
    # Customer segment risk
    if transaction.customer_segment == CustomerSegment.STANDARD:
        risk_score += 0.2
        reasons.append("New user segment")
    elif transaction.customer_segment == CustomerSegment.CHURN_RISK:
        risk_score += 0.3
        reasons.append("High churn risk")

    # Attempt count risk
    if transaction.attempt_count >= 2:
        risk_score += 0.3
        reasons.append("Multiple failed attempts")

    # Category risk
    if transaction.failure_category == FailureCategory.INSUFFICIENT_FUNDS:
        risk_score += 0.2
        reasons.append("Insufficient funds")

    risk_score = min(1.0, risk_score)
    reason_str = ", ".join(reasons) if reasons else "Normal transaction"
    
    return False, risk_score, reason_str

def is_duplicate(transaction_id: str) -> bool:
    """Check if we've already processed this transaction"""
    return transaction_id in _processed_transactions

def mark_processed(transaction_id: str) -> None:
    """Mark transaction as processed for dedup"""
    _processed_transactions.add(transaction_id)
