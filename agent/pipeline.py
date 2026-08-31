import time
import uuid
from typing import Optional
from config import get_settings
from schemas.transaction import Transaction, TransactionStatus
from schemas.decision import AgentDecision, RecoveryAction, GuardrailResult
from schemas.audit import AuditLog, AuditStage
from schemas.policy import MerchantPolicy

from agent.risk_detector import detect_risk, is_duplicate, mark_processed
from agent.context_builder import build_context
from agent.reasoner import AIReasoner
from agent.fallback_rules import deterministic_decision
from agent.guardrails import enforce_guardrails

class RecoveryPipeline:
    def __init__(self):
        self.reasoner = AIReasoner()
        self.settings = get_settings()
        self.policy = MerchantPolicy()
    
    def _create_audit_log(self, stage: AuditStage, input_data: dict, output_data: dict, start_time: float) -> AuditLog:
        return AuditLog(
            id=str(uuid.uuid4()),
            stage=stage,
            input_data=input_data,
            output_data=output_data,
            duration_ms=int((time.time() - start_time) * 1000)
        )

    async def process_transaction(self, transaction: Transaction) -> tuple[Optional[AgentDecision], Optional[GuardrailResult], list[AuditLog]]:
        """Process a single transaction through the full recovery pipeline."""
        audit_logs = []
        
        # Check duplicate
        if is_duplicate(transaction.id):
            return None, None, []
        mark_processed(transaction.id)

        # Stage 1: Risk Detection
        t0 = time.time()
        is_fatal, risk_score, risk_reason = detect_risk(transaction)
        audit_logs.append(self._create_audit_log(
            AuditStage.RISK_DETECTION,
            {"transaction_id": transaction.id},
            {"is_fatal": is_fatal, "risk_score": risk_score, "reason": risk_reason},
            t0
        ))
        
        if is_fatal:
            decision = AgentDecision(
                root_cause_analysis=risk_reason,
                recommended_action=RecoveryAction.NO_ACTION,
                confidence_score=1.0,
                risk_assessment="Fatal",
                reasoning="Fatal failure detected in risk stage."
            )
            return decision, GuardrailResult(passed_checks=[], blocked_checks=[], modified_action=decision.recommended_action, original_action=decision.recommended_action), audit_logs

        # Stage 2: Context Building  
        t1 = time.time()
        context = build_context(transaction)
        audit_logs.append(self._create_audit_log(
            AuditStage.CONTEXT_BUILDING,
            {"transaction_id": transaction.id},
            context,
            t1
        ))
        
        # Stage 3: AI Reasoning (with fallback)
        t2 = time.time()
        decision = None
        used_fallback = False
        try:
            decision = await self.reasoner.reason(transaction, context)
        except Exception as e:
            print(f"AI Reasoner failed: {e}. Falling back to deterministic rules.")
            decision = deterministic_decision(transaction, context)
            used_fallback = True
            
        audit_logs.append(self._create_audit_log(
            AuditStage.REASONING,
            {"transaction_id": transaction.id, "context": context},
            {"decision": decision.model_dump(), "used_fallback": used_fallback},
            t2
        ))
        
        # Stage 4: Guardrail Enforcement
        t3 = time.time()
        guardrail_result = enforce_guardrails(transaction, decision, self.policy)
        decision.recommended_action = guardrail_result.modified_action
        
        audit_logs.append(self._create_audit_log(
            AuditStage.GUARDRAILS,
            {"decision": decision.model_dump()},
            {"result": guardrail_result.model_dump()},
            t3
        ))
        
        return decision, guardrail_result, audit_logs
    
    async def process_batch(self, transactions: list[Transaction]) -> list[tuple[Optional[AgentDecision], Optional[GuardrailResult], list[AuditLog]]]:
        """Process a batch of transactions."""
        results = []
        for txn in transactions:
            results.append(await self.process_transaction(txn))
        return results
