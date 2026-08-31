import random
from datetime import datetime, timezone
from schemas.transaction import Transaction
from schemas.decision import RecoveryAttempt

class ActionVerifier:
    """Post-action verification."""
    
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        
    async def verify(self, transaction: Transaction, attempt: RecoveryAttempt) -> RecoveryAttempt:
        """Verify the outcome of a recovery attempt."""
        
        if attempt.is_success:
            attempt.verification_status = "VERIFIED_SUCCESS"
        else:
            # 5% chance of false negative (race condition)
            if self.rng.random() < 0.05:
                attempt.is_success = True
                attempt.amount_recovered = transaction.amount_inr
                attempt.verification_status = "VERIFIED_SUCCESS"
                attempt.outcome_details += " (Recovered via race condition handling)"
            else:
                attempt.verification_status = "VERIFIED_FAILED"
                
        attempt.verified_at = datetime.now(timezone.utc)
        return attempt
