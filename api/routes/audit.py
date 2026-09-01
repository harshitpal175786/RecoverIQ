from fastapi import APIRouter, Query, HTTPException, Path, Body
from typing import List, Optional, Dict, Any
from schemas.audit import AuditLog, EscalationRecord
from data.db import (
    get_audit_logs,
    get_escalations,
    get_escalations_unresolved,
    resolve_escalation,
    get_transaction,
)

router = APIRouter(tags=["audit"])


@router.get("/logs/{transaction_id}")
async def get_transaction_logs(transaction_id: str = Path(...)):
    """Fetch audit trail logs for a specific transaction."""
    try:
        tx_logs = await get_audit_logs(transaction_id)
        # Serialize to dict list
        return [
            {
                "log_id": log.log_id,
                "transaction_id": log.transaction_id,
                "stage": log.stage,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "input_data": log.input_data_json,
                "output_data": log.output_data_json,
                "guardrails_applied": log.guardrails_applied_json,
                "guardrails_blocked": log.guardrails_blocked_json,
                "duration_ms": log.duration_ms,
                "outcome": log.outcome,
            }
            for log in tx_logs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/escalations")
async def list_escalations(resolved: Optional[bool] = Query(None)):
    """Fetch all human-review escalation records with enriched transaction info."""
    try:
        if resolved is False:
            esc_list = await get_escalations_unresolved()
        elif resolved is True:
            esc_list = await get_escalations(resolved=True)
        else:
            esc_list = await get_escalations()

        enriched = []
        for esc in esc_list:
            tx = await get_transaction(esc.transaction_id)
            enriched.append({
                "escalation_id": esc.escalation_id,
                "transaction_id": esc.transaction_id,
                "reason": esc.reason,
                "priority": esc.priority,
                "resolved": esc.resolved,
                "created_at": esc.created_at.isoformat() if esc.created_at else None,
                "resolved_at": esc.resolved_at.isoformat() if esc.resolved_at else None,
                "resolution_notes": esc.resolution_notes,
                "customer_name": getattr(tx, "customer_name", "N/A") if tx else "N/A",
                "customer_segment": getattr(tx, "customer_segment", "STANDARD") if tx else "STANDARD",
                "amount_inr": getattr(tx, "amount_inr", 0.0) if tx else 0.0,
                "payment_method": getattr(tx, "payment_method", "N/A") if tx else "N/A",
                "failure_category": getattr(tx, "failure_category", "N/A") if tx else "N/A",
                "issuer_bank": getattr(tx, "issuer_bank", "N/A") if tx else "N/A",
            })

        return enriched
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation_endpoint(
    escalation_id: str = Path(...),
    notes: Optional[str] = Body("", embed=True),
):
    """Mark an escalation as resolved by a human operator."""
    try:
        success = await resolve_escalation(escalation_id, resolution_notes=notes)
        if not success:
            raise HTTPException(status_code=404, detail="Escalation record not found")
        return {"status": "resolved", "escalation_id": escalation_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
