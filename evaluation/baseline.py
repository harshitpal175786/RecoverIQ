import random
import uuid
from datetime import datetime, timezone
from schemas.transaction import Transaction, FailureCategory
from schemas.decision import RecoveryAction, RecoveryAttempt

class BaselineStrategy:
    """Naive single-retry baseline strategy representing merchant default behavior."""
    
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        # Immediate uncoordinated retry success probabilities
        self.baseline_probabilities = {
            FailureCategory.TRANSIENT_DOWNTIME: 0.35,  # Immediate retry often hits active bank outage
            FailureCategory.INSUFFICIENT_FUNDS: 0.05,  # Immediate retry fails before customer adds balance
            FailureCategory.USER_DROPOUT: 0.10,        # Server-side retry does not re-engage abandoned customer
            FailureCategory.LIMIT_EXCEEDED: 0.05,      # Retrying same card/UPI still exceeds limit
            FailureCategory.MANDATE_ISSUE: 0.05,       # Broken mandate fails on immediate retry
            FailureCategory.FATAL_DECLINE: 0.0,        # Hard blocked
        }
    
    async def process_transaction(self, transaction: Transaction) -> RecoveryAttempt:
        """Naive baseline: blind immediate single retry for all non-fatal failures."""
        if transaction.failure_category == FailureCategory.FATAL_DECLINE:
            action = RecoveryAction.NO_ACTION
            is_success = False
        else:
            action = RecoveryAction.RETRY
            prob = self.baseline_probabilities.get(transaction.failure_category, 0.15)
            is_success = self.rng.random() < prob
            
        amount_recovered = transaction.amount_inr if is_success else 0.0
        
        return RecoveryAttempt(
            attempt_id=str(uuid.uuid4()),
            transaction_id=transaction.transaction_id,
            action=action,
            success=is_success,
            amount_recovered_inr=amount_recovered,
            outcome_details="Naive single-retry baseline execution",
            executed_at=datetime.now(timezone.utc)
        )
