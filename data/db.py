import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, select, update
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

Base = declarative_base()

class TransactionModel(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    status = Column(String, index=True, nullable=False)
    failure_reason = Column(String, nullable=True)
    error_code = Column(String, nullable=True)
    bank_name = Column(String, nullable=True)
    upi_psp = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    customer_segment = Column(String, nullable=True)
    churn_risk_score = Column(Float, nullable=True)
    salary_day_estimate = Column(Integer, nullable=True)
    
    attempts = relationship("RecoveryAttemptModel", back_populates="transaction", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogModel", back_populates="transaction", cascade="all, delete-orphan")

class RecoveryAttemptModel(Base):
    __tablename__ = "recovery_attempts"
    
    id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    method = Column(String, nullable=False)
    status = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    transaction = relationship("TransactionModel", back_populates="attempts")

class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    action = Column(String, nullable=False)
    agent = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    transaction = relationship("TransactionModel", back_populates="audit_logs")

class EscalationRecordModel(Base):
    __tablename__ = "escalation_records"
    
    id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="UNRESOLVED")
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def save_transaction(transaction) -> TransactionModel:
    async with AsyncSessionLocal() as session:
        db_txn = TransactionModel(**transaction.model_dump())
        session.add(db_txn)
        await session.commit()
        await session.refresh(db_txn)
        return db_txn

async def save_transactions_batch(transactions: List) -> None:
    async with AsyncSessionLocal() as session:
        db_txns = [TransactionModel(**t.model_dump()) for t in transactions]
        session.add_all(db_txns)
        await session.commit()

async def get_transaction(transaction_id: str) -> Optional[TransactionModel]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(TransactionModel).where(TransactionModel.id == transaction_id))
        return result.scalars().first()

async def get_all_transactions() -> List[TransactionModel]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(TransactionModel))
        return result.scalars().all()

async def update_transaction_status(transaction_id: str, status: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(TransactionModel).where(TransactionModel.id == transaction_id).values(status=status)
        )
        await session.commit()

async def save_audit_log(audit_log) -> AuditLogModel:
    async with AsyncSessionLocal() as session:
        db_log = AuditLogModel(**audit_log.model_dump())
        session.add(db_log)
        await session.commit()
        await session.refresh(db_log)
        return db_log

async def get_audit_logs(transaction_id: str) -> List[AuditLogModel]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AuditLogModel).where(AuditLogModel.transaction_id == transaction_id))
        return result.scalars().all()

async def save_recovery_attempt(attempt) -> RecoveryAttemptModel:
    async with AsyncSessionLocal() as session:
        db_attempt = RecoveryAttemptModel(**attempt.model_dump())
        session.add(db_attempt)
        await session.commit()
        await session.refresh(db_attempt)
        return db_attempt

async def get_recovery_attempts(transaction_id: str) -> List[RecoveryAttemptModel]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RecoveryAttemptModel).where(RecoveryAttemptModel.transaction_id == transaction_id)
        )
        return result.scalars().all()

async def save_escalation(escalation) -> EscalationRecordModel:
    async with AsyncSessionLocal() as session:
        db_esc = EscalationRecordModel(**escalation.model_dump())
        session.add(db_esc)
        await session.commit()
        await session.refresh(db_esc)
        return db_esc

async def get_escalations() -> List[EscalationRecordModel]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(EscalationRecordModel))
        return result.scalars().all()

async def get_escalations_unresolved() -> List[EscalationRecordModel]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(EscalationRecordModel).where(EscalationRecordModel.status == "UNRESOLVED"))
        return result.scalars().all()
