from fastapi import APIRouter, Query, HTTPException, Path
from typing import List, Optional
from schemas.audit import AuditLog, EscalationRecord
from data.db import get_audit_logs, get_escalations, get_escalations_unresolved

router = APIRouter(tags=["audit"])

@router.get("/logs/{transaction_id}", response_model=List[AuditLog])
async def get_transaction_logs(transaction_id: str = Path(...)):
    try:
        all_logs = await get_audit_logs()
        tx_logs = [log for log in all_logs if getattr(log, 'transaction_id', None) == transaction_id]
        return tx_logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/escalations", response_model=List[EscalationRecord])
async def list_escalations(resolved: Optional[bool] = Query(None)):
    try:
        if resolved is False:
            return await get_escalations_unresolved()
            
        all_esc = await get_escalations()
        if resolved is True:
            return [e for e in all_esc if getattr(e, 'resolved', False)]
            
        return all_esc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
