"""Database layer with SQLAlchemy async models and CRUD operations."""

import json
import logging
from datetime import datetime
from typing import List, Optional, Any

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, select, update
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

Base = declarative_base()


class TransactionModel(Base):
    """SQLAlchemy model for transactions."""
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True, index=True)
    order_id = Column(String, nullable=True)
    customer_id = Column(String, index=True)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    customer_segment = Column(String, nullable=True)

    amount_inr = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    payment_method = Column(String, nullable=False)
    issuer_bank = Column(String, nullable=True)
    psp = Column(String, nullable=True)

    error_code = Column(String, nullable=True)
    error_source = Column(String, nullable=True)
    error_step = Column(String, nullable=True)
    error_reason = Column(String, nullable=True)
    error_description = Column(Text, nullable=True)

    failure_category = Column(String, nullable=False)
    attempt_count = Column(Integer, default=1)
    status = Column(String, index=True, nullable=False, default="FAILED")

    created_at = Column(DateTime, default=datetime.utcnow)
    failed_at = Column(DateTime, default=datetime.utcnow)

    customer_ltv_inr = Column(Float, default=0.0)
    historical_recovery_rate = Column(Float, default=0.5)
    churn_risk_score = Column(Float, default=0.5)
    preferred_channel = Column(String, default="WHATSAPP")
    salary_day_estimate = Column(Integer, nullable=True)
    previous_failures_30d = Column(Integer, default=0)

    business_model = Column(String, default="SaaS")
    is_recurring = Column(Boolean, default=False)
    subscription_id = Column(String, nullable=True)

    # Recovery result fields
    recovery_action = Column(String, nullable=True)
    recovered_amount_inr = Column(Float, default=0.0)
    recovery_decision_json = Column(Text, nullable=True)  # Store full AgentDecision as JSON
    batch_id = Column(String, nullable=True, index=True)


class RecoveryAttemptModel(Base):
    """SQLAlchemy model for recovery attempts."""
    __tablename__ = "recovery_attempts"

    attempt_id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, index=True, nullable=False)
    action = Column(String, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=False)
    outcome_details = Column(Text, default="")
    amount_recovered_inr = Column(Float, default=0.0)
    verification_status = Column(String, default="PENDING")
    verified_at = Column(DateTime, nullable=True)


class AuditLogModel(Base):
    """SQLAlchemy model for audit logs."""
    __tablename__ = "audit_logs"

    log_id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, index=True, nullable=False)
    batch_id = Column(String, nullable=True)
    stage = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    input_data_json = Column(Text, default="{}")
    output_data_json = Column(Text, default="{}")

    ai_used = Column(Boolean, default=False)
    ai_model = Column(String, nullable=True)
    ai_prompt = Column(Text, nullable=True)
    ai_raw_response = Column(Text, nullable=True)

    guardrails_applied_json = Column(Text, default="[]")
    guardrails_blocked_json = Column(Text, default="[]")

    duration_ms = Column(Float, default=0.0)
    error = Column(Text, nullable=True)
    outcome = Column(String, default="PENDING")


class EscalationRecordModel(Base):
    """SQLAlchemy model for escalation records."""
    __tablename__ = "escalation_records"

    escalation_id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, index=True, nullable=False)
    reason = Column(Text, nullable=False)
    priority = Column(String, default="MEDIUM")
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)


# Engine and session factory
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully")


# --- Transaction CRUD ---

async def save_transaction(transaction) -> None:
    """Save a single transaction to the database."""
    async with AsyncSessionLocal() as session:
        data = transaction.model_dump() if hasattr(transaction, 'model_dump') else transaction
        # Convert enums to strings
        for key, val in data.items():
            if hasattr(val, 'value'):
                data[key] = val.value
            elif isinstance(val, datetime):
                pass  # keep as-is
        db_txn = TransactionModel(**data)
        await session.merge(db_txn)  # Use merge for idempotency
        await session.commit()


async def save_transactions_batch(transactions: List, batch_id: str = None) -> None:
    """Save a batch of transactions to the database."""
    async with AsyncSessionLocal() as session:
        for t in transactions:
            data = t.model_dump() if hasattr(t, 'model_dump') else t
            for key, val in data.items():
                if hasattr(val, 'value'):
                    data[key] = val.value
            if batch_id:
                data['batch_id'] = batch_id
            db_txn = TransactionModel(**data)
            await session.merge(db_txn)
        await session.commit()
    logger.info(f"Saved batch of {len(transactions)} transactions")


async def get_transaction(transaction_id: str) -> Optional[TransactionModel]:
    """Get a single transaction by ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TransactionModel).where(TransactionModel.transaction_id == transaction_id)
        )
        return result.scalars().first()


async def get_all_transactions(status: str = None, limit: int = 500, offset: int = 0) -> List[TransactionModel]:
    """Get all transactions, optionally filtered by status."""
    async with AsyncSessionLocal() as session:
        query = select(TransactionModel)
        if status:
            query = query.where(TransactionModel.status == status)
        query = query.order_by(TransactionModel.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        return list(result.scalars().all())


async def update_transaction_status(transaction_id: str, status: str, recovery_action: str = None,
                                     recovered_amount: float = 0.0, decision_json: str = None) -> None:
    """Update transaction status and recovery details."""
    async with AsyncSessionLocal() as session:
        values = {"status": status}
        if recovery_action:
            values["recovery_action"] = recovery_action
        if recovered_amount > 0:
            values["recovered_amount_inr"] = recovered_amount
        if decision_json:
            values["recovery_decision_json"] = decision_json
        await session.execute(
            update(TransactionModel)
            .where(TransactionModel.transaction_id == transaction_id)
            .values(**values)
        )
        await session.commit()


async def get_transaction_count(status: str = None) -> int:
    """Get count of transactions."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import func
        query = select(func.count(TransactionModel.transaction_id))
        if status:
            query = query.where(TransactionModel.status == status)
        result = await session.execute(query)
        return result.scalar() or 0


# --- Audit Log CRUD ---

async def save_audit_log(audit_log) -> None:
    """Save an audit log entry."""
    async with AsyncSessionLocal() as session:
        data = audit_log.model_dump() if hasattr(audit_log, 'model_dump') else audit_log
        # Serialize complex fields
        for key in ['input_data', 'output_data']:
            if key in data and isinstance(data[key], dict):
                data[f'{key}_json'] = json.dumps(data.pop(key), default=str)
            elif key in data:
                data.pop(key)
        for key in ['guardrails_applied', 'guardrails_blocked']:
            if key in data and isinstance(data[key], list):
                data[f'{key}_json'] = json.dumps(data.pop(key))
            elif key in data:
                data.pop(key)
        # Convert enums
        for k, v in list(data.items()):
            if hasattr(v, 'value'):
                data[k] = v.value
        db_log = AuditLogModel(**data)
        await session.merge(db_log)
        await session.commit()


async def save_audit_logs_batch(audit_logs: List) -> None:
    """Save a batch of audit log entries."""
    for log in audit_logs:
        await save_audit_log(log)


async def get_audit_logs(transaction_id: str) -> List[AuditLogModel]:
    """Get all audit logs for a transaction."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.transaction_id == transaction_id)
            .order_by(AuditLogModel.timestamp)
        )
        return list(result.scalars().all())


# --- Recovery Attempt CRUD ---

async def save_recovery_attempt(attempt) -> None:
    """Save a recovery attempt."""
    async with AsyncSessionLocal() as session:
        data = attempt.model_dump() if hasattr(attempt, 'model_dump') else attempt
        for k, v in list(data.items()):
            if hasattr(v, 'value'):
                data[k] = v.value
        db_attempt = RecoveryAttemptModel(**data)
        await session.merge(db_attempt)
        await session.commit()


async def get_recovery_attempts(transaction_id: str) -> List[RecoveryAttemptModel]:
    """Get all recovery attempts for a transaction."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RecoveryAttemptModel)
            .where(RecoveryAttemptModel.transaction_id == transaction_id)
            .order_by(RecoveryAttemptModel.executed_at)
        )
        return list(result.scalars().all())


# --- Escalation CRUD ---

async def save_escalation(escalation) -> None:
    """Save an escalation record."""
    async with AsyncSessionLocal() as session:
        data = escalation.model_dump() if hasattr(escalation, 'model_dump') else escalation
        for k, v in list(data.items()):
            if hasattr(v, 'value'):
                data[k] = v.value
        db_esc = EscalationRecordModel(**data)
        await session.merge(db_esc)
        await session.commit()


async def get_escalations(resolved: bool = None) -> List[EscalationRecordModel]:
    """Get escalation records, optionally filtered by resolved status."""
    async with AsyncSessionLocal() as session:
        query = select(EscalationRecordModel).order_by(EscalationRecordModel.created_at.desc())
        if resolved is not None:
            query = query.where(EscalationRecordModel.resolved == resolved)
        result = await session.execute(query)
        return list(result.scalars().all())


async def get_escalations_unresolved() -> List[EscalationRecordModel]:
    """Get unresolved escalation records."""
    return await get_escalations(resolved=False)


async def resolve_escalation(escalation_id: str, resolution_notes: str = "") -> bool:
    """Mark an escalation as resolved with human reviewer notes."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(EscalationRecordModel)
            .where(EscalationRecordModel.escalation_id == escalation_id)
            .values(resolved=True, resolved_at=datetime.utcnow(), resolution_notes=resolution_notes)
        )
        await session.commit()
        return result.rowcount > 0

