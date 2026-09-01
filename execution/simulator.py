import random
import uuid
from datetime import datetime, timezone
from schemas.transaction import Transaction, FailureCategory
from schemas.decision import RecoveryAction, RecoveryAttempt

class SimulatorExecutor:
    """Simulated execution engine that mocks payment recovery actions."""
    
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        
        # Realistic recovery probabilities by (FailureCategory, RecoveryAction)
        self.success_probabilities = {
            (FailureCategory.TRANSIENT_DOWNTIME, RecoveryAction.RETRY): 0.75,
            (FailureCategory.TRANSIENT_DOWNTIME, RecoveryAction.DELAY_AND_RETRY): 0.80,
            (FailureCategory.TRANSIENT_DOWNTIME, RecoveryAction.ALTERNATE_METHOD): 0.65,
            (FailureCategory.INSUFFICIENT_FUNDS, RecoveryAction.DELAY_AND_RETRY): 0.65,
            (FailureCategory.INSUFFICIENT_FUNDS, RecoveryAction.PAYMENT_LINK): 0.50,
            (FailureCategory.INSUFFICIENT_FUNDS, RecoveryAction.RETRY): 0.15,
            (FailureCategory.USER_DROPOUT, RecoveryAction.PAYMENT_LINK): 0.60,
            (FailureCategory.USER_DROPOUT, RecoveryAction.DELAY_AND_RETRY): 0.55,
            (FailureCategory.USER_DROPOUT, RecoveryAction.ALTERNATE_METHOD): 0.55,
            (FailureCategory.USER_DROPOUT, RecoveryAction.RETRY): 0.20,
            (FailureCategory.MANDATE_ISSUE, RecoveryAction.PAYMENT_LINK): 0.55,
            (FailureCategory.MANDATE_ISSUE, RecoveryAction.ALTERNATE_METHOD): 0.60,
            (FailureCategory.MANDATE_ISSUE, RecoveryAction.DELAY_AND_RETRY): 0.50,
            (FailureCategory.MANDATE_ISSUE, RecoveryAction.RETRY): 0.10,
            (FailureCategory.LIMIT_EXCEEDED, RecoveryAction.ALTERNATE_METHOD): 0.70,
            (FailureCategory.LIMIT_EXCEEDED, RecoveryAction.DELAY_AND_RETRY): 0.65,
            (FailureCategory.LIMIT_EXCEEDED, RecoveryAction.PAYMENT_LINK): 0.55,
            (FailureCategory.LIMIT_EXCEEDED, RecoveryAction.RETRY): 0.10,
        }

    async def execute(self, transaction: Transaction, action: RecoveryAction, retry_delay_minutes: int = 0) -> RecoveryAttempt:
        """Simulate executing a recovery action."""
        success_prob = 0.0
        
        if transaction.failure_category == FailureCategory.FATAL_DECLINE:
            success_prob = 0.05
        elif action == RecoveryAction.NO_ACTION:
            success_prob = 0.0
        elif action == RecoveryAction.ESCALATE:
            success_prob = 0.40
        else:
            success_prob = self.success_probabilities.get((transaction.failure_category, action), 0.10)
        
        is_success = self.rng.random() < success_prob
        amount_recovered = transaction.amount_inr if is_success else 0.0
        
        outcome_details = f"Action {action.name} resulted in {'success' if is_success else 'failure'}."
        
        return RecoveryAttempt(
            attempt_id=str(uuid.uuid4()),
            transaction_id=transaction.transaction_id,
            action=action,
            success=is_success,
            amount_recovered_inr=amount_recovered,
            outcome_details=outcome_details,
            executed_at=datetime.now(timezone.utc)
        )
