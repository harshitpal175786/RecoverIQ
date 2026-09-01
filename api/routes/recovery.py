from fastapi import APIRouter, Query, HTTPException, Path
from schemas.transaction import TransactionStatus, Transaction
from data.db import (
    get_all_transactions,
    get_transaction,
    save_recovery_attempt,
    save_audit_log,
    update_transaction_status
)
from agent.pipeline import RecoveryPipeline
from execution.simulator import SimulatorExecutor
from execution.verifier import ActionVerifier

router = APIRouter(tags=["recovery"])

@router.post("/run")
async def run_recovery(
    use_ai: bool = Query(True),
    batch_size: int = Query(0, description="0 means all FAILED transactions")
):
    try:
        all_transactions = await get_all_transactions()
        failed_tx = [t for t in all_transactions if t.status == TransactionStatus.FAILED]
        
        if batch_size > 0:
            failed_tx = failed_tx[:batch_size]
            
        pipeline = RecoveryPipeline()
        simulator = SimulatorExecutor()
        verifier = ActionVerifier()
        
        processed = 0
        recovered = 0
        escalated = 0
        total_recovered_inr = 0.0
        
        for tx_model in failed_tx:
            # Convert SQLAlchemy model to Pydantic model
            tx = Transaction.model_validate(tx_model, from_attributes=True)
            decision, guardrail_result, audit_logs = await pipeline.process_transaction(tx)
            
            for log in audit_logs:
                await save_audit_log(log)
            
            attempt = await simulator.execute(tx, decision.recommended_action, retry_delay_minutes=0)
            verified_attempt = await verifier.verify(tx, attempt)
            
            await save_recovery_attempt(verified_attempt)
            
            if verified_attempt.success:
                await update_transaction_status(tx.transaction_id, TransactionStatus.RECOVERED.value)
                recovered += 1
                total_recovered_inr += tx.amount_inr
            elif getattr(decision.recommended_action, 'type', '') == "escalate" or getattr(decision.recommended_action, 'name', '') == "escalate":
                await update_transaction_status(tx.transaction_id, TransactionStatus.ESCALATED.value)
                escalated += 1
                
            processed += 1
            
        return {
            "processed": processed,
            "recovered": recovered,
            "escalated": escalated,
            "total_recovered_inr": total_recovered_inr
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from schemas.transaction import TransactionStatus, Transaction

@router.post("/recovery/{transaction_id}/execute")
async def execute_recovery(transaction_id: str = Path(...)):
    try:
        tx_model = await get_transaction(transaction_id)
        if not tx_model:
            raise HTTPException(status_code=404, detail="Transaction not found")
            
        tx = Transaction.model_validate(tx_model, from_attributes=True)
        pipeline = RecoveryPipeline()
        simulator = SimulatorExecutor()
        verifier = ActionVerifier()
        
        decision, guardrail_result, audit_logs = await pipeline.process_transaction(tx)
        
        for log in audit_logs:
            await save_audit_log(log)
            
        attempt = await simulator.execute(tx, decision.recommended_action, retry_delay_minutes=0)
        verified_attempt = await verifier.verify(tx, attempt)
        
        await save_recovery_attempt(verified_attempt)
        
        if verified_attempt.success:
            await update_transaction_status(tx.transaction_id, TransactionStatus.RECOVERED.value)
        
        return {
            "transaction_id": transaction_id,
            "decision": decision,
            "guardrail_result": guardrail_result,
            "attempt": verified_attempt
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
