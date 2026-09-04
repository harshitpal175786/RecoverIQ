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
    
    def _create_audit_log(self, transaction_id: str, stage: AuditStage, input_data: dict, output_data: dict, start_time: float) -> AuditLog:
        return AuditLog(
            log_id=str(uuid.uuid4()),
            transaction_id=transaction_id,
            stage=stage,
            input_data=input_data,
            output_data=output_data,
            duration_ms=float(int((time.time() - start_time) * 1000))
        )

    async def process_transaction(self, transaction: Transaction, use_ai: bool = True, force: bool = False) -> tuple[Optional[AgentDecision], Optional[GuardrailResult], list[AuditLog]]:
        """Process a single transaction through the full recovery pipeline."""
        audit_logs = []
        
        # Check duplicate (allow explicit manual execution with force=True)
        if not force and is_duplicate(transaction.transaction_id):
            return None, None, []
        mark_processed(transaction.transaction_id)

        # Stage 1: Risk Detection
        t0 = time.time()
        is_fatal, risk_score, risk_reason = detect_risk(transaction)
        audit_logs.append(self._create_audit_log(
            transaction.transaction_id,
            AuditStage.RISK_DETECTION,
            {"transaction_id": transaction.transaction_id},
            {"is_fatal": is_fatal, "risk_score": risk_score, "reason": risk_reason},
            t0
        ))
        
        if is_fatal:
            decision = AgentDecision(
                transaction_id=transaction.transaction_id,
                root_cause_analysis=risk_reason,
                recommended_action=RecoveryAction.NO_ACTION,
                confidence_score=1.0,
                risk_assessment="Fatal",
                reasoning="Fatal failure detected in risk stage."
            )
            return decision, GuardrailResult(passed=True, checks_applied=[], checks_blocked=[], final_action=decision.recommended_action, original_action=decision.recommended_action, modifications=[]), audit_logs

        # Stage 2: Context Building  
        t1 = time.time()
        context = build_context(transaction)
        audit_logs.append(self._create_audit_log(
            transaction.transaction_id,
            AuditStage.CONTEXT_BUILDING,
            {"transaction_id": transaction.transaction_id},
            context,
            t1
        ))
        
        # Stage 3: AI Reasoning (with fallback)
        t2 = time.time()
        decision = None
        used_fallback = False
        if use_ai:
            try:
                decision = await self.reasoner.reason(transaction, context)
            except Exception as e:
                print(f"AI Reasoner failed: {e}. Falling back to deterministic rules.")
                decision = deterministic_decision(transaction, context)
                used_fallback = True
        else:
            decision = deterministic_decision(transaction, context)
            used_fallback = True
            
        audit_logs.append(self._create_audit_log(
            transaction.transaction_id,
            AuditStage.AI_REASONING,
            {"transaction_id": transaction.transaction_id, "context": context},
            {"decision": decision.model_dump(), "used_fallback": used_fallback},
            t2
        ))
        
        # Stage 4: Guardrail Enforcement
        t3 = time.time()
        guardrail_result = enforce_guardrails(transaction, decision, self.policy)
        decision.recommended_action = guardrail_result.final_action
        
        audit_logs.append(self._create_audit_log(
            transaction.transaction_id,
            AuditStage.GUARDRAIL_CHECK,
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
