import random
import uuid
from datetime import datetime, timezone
from schemas.transaction import Transaction, FailureCategory
from schemas.decision import RecoveryAction, RecoveryAttempt

class BaselineStrategy:
    """Naive single-retry baseline strategy."""
    
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
    
    async def process_transaction(self, transaction: Transaction) -> RecoveryAttempt:
        """Naive baseline: single immediate retry for all non-fatal failures."""
        if transaction.failure_category == FailureCategory.FATAL_DECLINE:
            action = RecoveryAction.NO_ACTION
            is_success = False
        else:
            action = RecoveryAction.RETRY
            is_success = self.rng.random() < 0.20
            
        amount_recovered = transaction.amount_inr if is_success else 0.0
        
        return RecoveryAttempt(
            attempt_id=str(uuid.uuid4()),
            transaction_id=transaction.transaction_id,
            action=action,
            is_success=is_success,
            amount_recovered=amount_recovered,
            outcome_details="Baseline execution",
            attempted_at=datetime.now(timezone.utc)
        )
