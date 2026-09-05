from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class PaymentMethod(str, Enum):
    UPI_INTENT = "UPI_INTENT"
    UPI_COLLECT = "UPI_COLLECT"
    UPI_AUTOPAY = "UPI_AUTOPAY"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    NETBANKING = "NETBANKING"
    E_NACH = "E_NACH"
    WALLET = "WALLET"

class FailureCategory(str, Enum):
    TRANSIENT_DOWNTIME = "TRANSIENT_DOWNTIME"  # NPCI/Bank timeout -> retry
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"  # Low balance -> delay + nudge
    USER_DROPOUT = "USER_DROPOUT"              # OTP expired -> payment link
    MANDATE_ISSUE = "MANDATE_ISSUE"            # Recurring auth fail -> re-auth
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"          # Daily limit -> alternate method
    FATAL_DECLINE = "FATAL_DECLINE"            # Card blocked/expired -> escalate

class CustomerSegment(str, Enum):
    VIP = "VIP"
    HIGH_VALUE = "HIGH_VALUE"
    STANDARD = "STANDARD"
    CHURN_RISK = "CHURN_RISK"

class TransactionStatus(str, Enum):
    FAILED = "FAILED"
    PENDING_RECOVERY = "PENDING_RECOVERY"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"
    RECOVERED = "RECOVERED"
    ESCALATED = "ESCALATED"
    ABANDONED = "ABANDONED"

class Transaction(BaseModel):
    """Represents a failed payment transaction that needs recovery."""
    transaction_id: str = Field(..., description="Unique transaction ID")
    order_id: Optional[str] = Field(None, description="Associated order ID")
    customer_id: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_segment: CustomerSegment = CustomerSegment.STANDARD
    
    amount_inr: float = Field(..., gt=0)
    currency: str = "INR"
    payment_method: PaymentMethod
    issuer_bank: str = Field(..., description="HDFC | SBI | ICICI | AXIS | KOTAK | YES")
    psp: Optional[str] = Field(None, description="UPI PSP: PHONEPE | GPAY | PAYTM | CRED")
    
    # Razorpay error structure
    error_code: str = Field(..., description="e.g. BAD_REQUEST_ERROR")
    error_source: str = Field(..., description="customer | gateway | business | internal")
    error_step: str = Field(..., description="payment_initiation | payment_authentication | payment_authorization")
    error_reason: str = Field(..., description="e.g. insufficient_funds, payment_timed_out")
    error_description: str = Field("", description="Human-readable error description")
    
    failure_category: FailureCategory
    attempt_count: int = Field(1, ge=1)
    status: TransactionStatus = TransactionStatus.FAILED
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    failed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Customer context (for AI reasoning)
    customer_ltv_inr: Optional[float] = Field(0.0, ge=0)
    historical_recovery_rate: Optional[float] = Field(0.5, ge=0.0, le=1.0)
    churn_risk_score: Optional[float] = Field(0.5, ge=0.0, le=1.0)
    preferred_channel: Optional[str] = Field("WHATSAPP", description="WHATSAPP | SMS | EMAIL | IN_APP")
    salary_day_estimate: Optional[int] = Field(None, ge=1, le=31)
    previous_failures_30d: Optional[int] = Field(0, ge=0)
    
    # Business context
    business_model: Optional[str] = Field("SaaS", description="SaaS | E_COMMERCE | SUBSCRIPTION | LENDING")
    is_recurring: Optional[bool] = False
    subscription_id: Optional[str] = None

    # AI Recovery Results
    recovery_action: Optional[str] = None
    recovered_amount_inr: Optional[float] = 0.0
    recovery_decision_json: Optional[str] = None

class TransactionBatch(BaseModel):
    """A batch of transactions for evaluation."""
    transactions: list[Transaction]
    batch_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    total_count: int = 0
    total_amount_inr: float = 0.0
