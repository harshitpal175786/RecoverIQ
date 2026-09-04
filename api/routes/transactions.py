from fastapi import APIRouter, Query, HTTPException, Path
from typing import List, Optional
from schemas.transaction import Transaction, TransactionStatus
from data.db import get_all_transactions, get_transaction, get_recovery_attempts, get_audit_logs

router = APIRouter(tags=["transactions"])

@router.get("/transactions", response_model=List[Transaction])
async def list_transactions(
    status: Optional[TransactionStatus] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        all_tx = await get_all_transactions()
        if status:
            if status == TransactionStatus.PENDING_RECOVERY:
                all_tx = [t for t in all_tx if t.status in [TransactionStatus.FAILED, TransactionStatus.PENDING_RECOVERY, "FAILED", "PENDING_RECOVERY"]]
            else:
                all_tx = [t for t in all_tx if t.status == status or getattr(t.status, 'value', str(t.status)) == getattr(status, 'value', str(status))]
            
        return all_tx[offset:offset+limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions/{transaction_id}")
async def get_transaction_detail(transaction_id: str = Path(...)):
    try:
        tx = await get_transaction(transaction_id)
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")
            
        tx_attempts = await get_recovery_attempts(transaction_id)
        tx_logs = await get_audit_logs(transaction_id)
        
        return {
            "transaction": tx,
            "recovery_attempts": tx_attempts,
            "audit_logs": tx_logs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

