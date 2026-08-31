import uuid
from schemas.transaction import Transaction
from schemas.metrics import RecoveryMetrics, ComparisonReport
from execution.simulator import SimulatorExecutor
from execution.verifier import ActionVerifier
from evaluation.baseline import BaselineStrategy
from evaluation.metrics import compute_metrics, compute_comparison

class RecoveryPipeline:
    """Dummy pipeline to avoid circular imports. Replace with actual pipeline."""
    async def process(self, transaction):
        # Return mock decision and guardrail for now
        from schemas.decision import AgentDecision, RecoveryAction, GuardrailResult
        return AgentDecision(
            transaction_id=transaction.transaction_id,
            recommended_action=RecoveryAction.RETRY,
            confidence_score=0.9,
            reasoning="Mock reasoning"
        ), GuardrailResult(is_safe=True)

class EvaluationRunner:
    """Batch evaluation runner."""
    
    def __init__(self):
        # In a real setup, pipeline would be injected
        self.pipeline = RecoveryPipeline()
        self.simulator = SimulatorExecutor(seed=42)
        self.verifier = ActionVerifier(seed=42)
        self.baseline = BaselineStrategy(seed=42)
    
    async def run_recoveriq(self, transactions: list[Transaction]) -> RecoveryMetrics:
        """Run full RecoverIQ pipeline on a batch."""
        attempts = []
        decisions = []
        
        for tx in transactions:
            decision, guardrail = await self.pipeline.process(tx)
            decisions.append(decision)
            
            attempt = await self.simulator.execute(tx, decision.recommended_action)
            attempt = await self.verifier.verify(tx, attempt)
            attempts.append(attempt)
            
        return compute_metrics("batch_1", "RecoverIQ", transactions, attempts, decisions)
    
    async def run_baseline(self, transactions: list[Transaction]) -> RecoveryMetrics:
        """Run naive baseline on same batch."""
        attempts = []
        
        for tx in transactions:
            attempt = await self.baseline.process_transaction(tx)
            attempt = await self.verifier.verify(tx, attempt)
            attempts.append(attempt)
            
        return compute_metrics("batch_1", "Baseline", transactions, attempts)
    
    async def run_comparison(self, transactions: list[Transaction]) -> ComparisonReport:
        """Run both strategies and compare."""
        baseline_metrics = await self.run_baseline(transactions)
        recoveriq_metrics = await self.run_recoveriq(transactions)
        
        return compute_comparison(baseline_metrics, recoveriq_metrics)
