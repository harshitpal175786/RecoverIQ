"""Recovery pipeline API routes."""

import json
import uuid
from pathlib import Path as FilePath
from fastapi import APIRouter, Query, HTTPException, Path
from schemas.transaction import TransactionStatus, Transaction
from schemas.decision import RecoveryAction
from schemas.audit import EscalationRecord
from data.db import (
    get_all_transactions,
    get_transaction,
    save_transaction,
    save_recovery_attempt,
    save_audit_log,
    save_audit_logs_batch,
    save_escalation,
    update_transaction_status,
)
from agent.pipeline import RecoveryPipeline
from execution.simulator import SimulatorExecutor
from execution.verifier import ActionVerifier

router = APIRouter(tags=["recovery"])


async def _handle_escalation_if_needed(tx: Transaction, decision, guardrail_result):
    """Helper to persist escalation records when guardrails or AI escalates."""
    if decision.recommended_action == RecoveryAction.ESCALATE or (guardrail_result and guardrail_result.final_action == RecoveryAction.ESCALATE):
        reason = "; ".join(guardrail_result.checks_blocked) if (guardrail_result and guardrail_result.checks_blocked) else decision.root_cause_analysis
        priority = "CRITICAL" if tx.amount_inr > 100000 else ("HIGH" if (tx.amount_inr > 50000 or getattr(tx.customer_segment, 'value', '') in ['VIP', 'HIGH_VALUE']) else "MEDIUM")
        
        esc = EscalationRecord(
            escalation_id=f"esc_{tx.transaction_id}",
            transaction_id=tx.transaction_id,
            reason=reason or "Escalated by Guardrails / Policy",
            priority=priority,
        )
        await save_escalation(esc)


@router.post("/run")
async def run_recovery(
    use_ai: bool = Query(True),
    batch_size: int = Query(0, description="0 means all FAILED transactions"),
):
    """Run the recovery pipeline on failed transactions with concurrent execution."""
    try:
        import asyncio
        all_transactions = await get_all_transactions(status="FAILED")

        if batch_size > 0:
            all_transactions = all_transactions[:batch_size]

        if not all_transactions:
            return {
                "processed": 0, "recovered": 0, "escalated": 0,
                "total_recovered_inr": 0.0, "message": "No failed transactions found. Run POST /seed first."
            }

        pipeline = RecoveryPipeline()
        simulator = SimulatorExecutor()
        verifier = ActionVerifier()

        sem = asyncio.Semaphore(15)

        async def process_single(tx_model):
            async with sem:
                try:
                    tx = Transaction.model_validate(tx_model, from_attributes=True)
                    decision, guardrail_result, audit_logs = await pipeline.process_transaction(tx, use_ai=use_ai)

                    if not decision:
                        return "skipped", 0.0

                    # Save audit logs
                    await save_audit_logs_batch(audit_logs)

                    # Execute the recovery action
                    attempt = await simulator.execute(tx, decision.recommended_action, retry_delay_minutes=decision.retry_delay_minutes)
                    verified_attempt = await verifier.verify(tx, attempt)
                    await save_recovery_attempt(verified_attempt)

                    # Handle escalation record persistence
                    await _handle_escalation_if_needed(tx, decision, guardrail_result)

                    # Update transaction status and save decision
                    action_name = decision.recommended_action.value
                    decision_json = decision.model_dump_json()

                    if verified_attempt.success:
                        await update_transaction_status(
                            tx.transaction_id, "RECOVERED",
                            recovery_action=action_name,
                            recovered_amount=verified_attempt.amount_recovered_inr,
                            decision_json=decision_json,
                        )
                        return "recovered", verified_attempt.amount_recovered_inr
                    elif decision.recommended_action == RecoveryAction.ESCALATE or (guardrail_result and guardrail_result.final_action == RecoveryAction.ESCALATE):
                        await update_transaction_status(
                            tx.transaction_id, "ESCALATED",
                            recovery_action=action_name,
                            decision_json=decision_json,
                        )
                        return "escalated", 0.0
                    elif decision.recommended_action == RecoveryAction.NO_ACTION:
                        await update_transaction_status(
                            tx.transaction_id, "ABANDONED",
                            recovery_action=action_name,
                            decision_json=decision_json,
                        )
                        return "abandoned", 0.0
                    else:
                        await update_transaction_status(
                            tx.transaction_id, "RECOVERY_IN_PROGRESS",
                            recovery_action=action_name,
                            decision_json=decision_json,
                        )
                        return "in_progress", 0.0
                except Exception as e:
                    print(f"Error processing transaction: {e}")
                    return "error", 0.0

        results = await asyncio.gather(*(process_single(tx_m) for tx_m in all_transactions))

        processed = len(results)
        recovered = sum(1 for status, _ in results if status == "recovered")
        escalated = sum(1 for status, _ in results if status == "escalated")
        total_recovered_inr = sum(amt for _, amt in results)

        return {
            "processed": processed,
            "recovered": recovered,
            "escalated": escalated,
            "total_recovered_inr": round(total_recovered_inr, 2),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/recovery/{transaction_id}/execute")
async def execute_recovery(transaction_id: str = Path(...)):
    """Process a single transaction through the recovery pipeline."""
    try:
        tx_model = await get_transaction(transaction_id)
        if not tx_model:
            raise HTTPException(status_code=404, detail="Transaction not found")

        tx = Transaction.model_validate(tx_model, from_attributes=True)
        pipeline = RecoveryPipeline()
        simulator = SimulatorExecutor()
        verifier = ActionVerifier()

        decision, guardrail_result, audit_logs = await pipeline.process_transaction(tx, force=True)

        if not decision:
            return {"transaction_id": transaction_id, "message": "Skipped (duplicate or already processed)"}

        await save_audit_logs_batch(audit_logs)

        attempt = await simulator.execute(tx, decision.recommended_action, retry_delay_minutes=decision.retry_delay_minutes)
        verified_attempt = await verifier.verify(tx, attempt)
        await save_recovery_attempt(verified_attempt)

        await _handle_escalation_if_needed(tx, decision, guardrail_result)

        action_name = decision.recommended_action.value
        decision_json = decision.model_dump_json()

        if verified_attempt.success:
            await update_transaction_status(
                tx.transaction_id, "RECOVERED",
                recovery_action=action_name,
                recovered_amount=verified_attempt.amount_recovered_inr,
                decision_json=decision_json,
            )
        elif decision.recommended_action == RecoveryAction.ESCALATE or (guardrail_result and guardrail_result.final_action == RecoveryAction.ESCALATE):
            await update_transaction_status(tx.transaction_id, "ESCALATED", recovery_action=action_name, decision_json=decision_json)

        return {
            "transaction_id": transaction_id,
            "decision": decision.model_dump(),
            "guardrail_result": guardrail_result.model_dump() if guardrail_result else None,
            "attempt": verified_attempt.model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/scenarios")
async def run_demo_scenarios():
    """Run the 4 official SRS Demo Scenarios and return execution report."""
    try:
        scenarios_file = FilePath(__file__).parent.parent.parent / "data" / "seed_scenarios.json"
        if not scenarios_file.exists():
            raise HTTPException(status_code=404, detail="Seed scenarios file not found")

        with open(scenarios_file, "r") as f:
            scenarios = json.load(f)

        pipeline = RecoveryPipeline()
        simulator = SimulatorExecutor(seed=42)
        verifier = ActionVerifier(seed=42)

        results = []

        for sc in scenarios:
            tx_data = sc["transaction"]
            tx = Transaction(**tx_data)
            await save_transaction(tx)

            # In scenario 4, if payment is already recovered, guardrails will prevent duplicate action
            decision, guardrail_result, audit_logs = await pipeline.process_transaction(tx)
            
            attempt = None
            verified_attempt = None
            if decision:
                await save_audit_logs_batch(audit_logs)
                attempt = await simulator.execute(tx, decision.recommended_action, retry_delay_minutes=decision.retry_delay_minutes)
                verified_attempt = await verifier.verify(tx, attempt)
                await save_recovery_attempt(verified_attempt)
                await _handle_escalation_if_needed(tx, decision, guardrail_result)

                action_name = decision.recommended_action.value
                decision_json = decision.model_dump_json()

                if verified_attempt.success:
                    await update_transaction_status(
                        tx.transaction_id, "RECOVERED",
                        recovery_action=action_name,
                        recovered_amount=verified_attempt.amount_recovered_inr,
                        decision_json=decision_json,
                    )
                elif decision.recommended_action == RecoveryAction.ESCALATE or (guardrail_result and guardrail_result.final_action == RecoveryAction.ESCALATE):
                    await update_transaction_status(tx.transaction_id, "ESCALATED", recovery_action=action_name, decision_json=decision_json)

            results.append({
                "scenario_id": sc["scenario_id"],
                "title": sc["title"],
                "description": sc["description"],
                "transaction_id": tx.transaction_id,
                "amount_inr": tx.amount_inr,
                "expected_action": sc["expected_action"],
                "actual_action": decision.recommended_action.value if decision else "SKIPPED",
                "guardrail_passed": guardrail_result.passed if guardrail_result else False,
                "guardrail_modifications": guardrail_result.modifications if guardrail_result else [],
                "confidence_score": decision.confidence_score if decision else 1.0,
                "reasoning": decision.reasoning if decision else "No decision needed.",
                "verification_status": verified_attempt.verification_status if verified_attempt else "VERIFIED_SKIPPED",
                "success": verified_attempt.success if verified_attempt else False,
            })

        return {"scenarios": results, "count": len(results)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

