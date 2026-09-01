"""Batch evaluation runner — compares RecoverIQ vs naive baseline."""

from schemas.transaction import Transaction
from schemas.metrics import RecoveryMetrics, ComparisonReport
from agent.pipeline import RecoveryPipeline
from execution.simulator import SimulatorExecutor
from execution.verifier import ActionVerifier
from evaluation.baseline import BaselineStrategy
from evaluation.metrics import compute_metrics, compute_comparison


class EvaluationRunner:
    """Batch evaluation runner."""

    def __init__(self, seed: int = 42):
        self.pipeline = RecoveryPipeline()
        self.simulator = SimulatorExecutor(seed=seed)
        self.verifier = ActionVerifier(seed=seed)
        self.baseline = BaselineStrategy(seed=seed)

    async def run_recoveriq(self, transactions: list[Transaction]) -> RecoveryMetrics:
        """Run full RecoverIQ pipeline on a batch."""
        attempts = []
        decisions = []

        for tx in transactions:
            try:
                decision, guardrail_result, audit_logs = await self.pipeline.process_transaction(tx)
                if decision:
                    decisions.append(decision)
                    attempt = await self.simulator.execute(tx, decision.recommended_action)
                    attempt = await self.verifier.verify(tx, attempt)
                    attempts.append(attempt)
            except Exception as e:
                # Log and continue — don't let one failure block the batch
                print(f"Error processing {tx.transaction_id}: {e}")
                continue

        return compute_metrics("eval_riq", "RECOVERIQ", transactions, attempts, decisions)

    async def run_baseline(self, transactions: list[Transaction]) -> RecoveryMetrics:
        """Run naive baseline on same batch."""
        attempts = []

        for tx in transactions:
            attempt = await self.baseline.process_transaction(tx)
            attempt = await self.verifier.verify(tx, attempt)
            attempts.append(attempt)

        return compute_metrics("eval_bl", "BASELINE", transactions, attempts)

    async def run_comparison(self, transactions: list[Transaction]) -> ComparisonReport:
        """Run both strategies and compare."""
        baseline_metrics = await self.run_baseline(transactions)
        recoveriq_metrics = await self.run_recoveriq(transactions)

        return compute_comparison(baseline_metrics, recoveriq_metrics)
