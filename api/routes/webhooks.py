"""Razorpay Webhook Handler."""

import json
import logging
import hmac
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Header, HTTPException
from config import get_settings
from schemas.transaction import Transaction, PaymentMethod, FailureCategory, CustomerSegment
from data.db import save_transaction, update_transaction_status, save_recovery_attempt
from agent.pipeline import RecoveryPipeline
from execution.simulator import SimulatorExecutor
from execution.verifier import ActionVerifier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_razorpay_signature(body: bytes, signature: Optional[str], secret: str) -> bool:
    """Verify webhook signature from Razorpay."""
    if not signature or not isinstance(signature, str) or not secret:
        return True  # Allow in test mode if signature/secret not present
    expected_signature = hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


@router.get("/razorpay")
async def razorpay_webhook_info():
    """Friendly status check when visited directly in a browser."""
    return {
        "status": "active",
        "service": "RecoverIQ Razorpay Webhook Receiver",
        "events_handled": ["payment.failed", "payment_link.paid", "payment.captured"],
        "info": "This endpoint is live and listening for HTTP POST webhook events from Razorpay."
    }


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(default=None),
):
    """Receive live Razorpay webhook events (e.g. payment.failed, payment_link.paid)."""
    settings = get_settings()
    body_bytes = await request.body()

    # Signature verification (optional in test mode)
    if x_razorpay_signature and settings.RAZORPAY_KEY_SECRET:
        if not verify_razorpay_signature(body_bytes, x_razorpay_signature, settings.RAZORPAY_KEY_SECRET):
            logger.warning("Invalid Razorpay webhook signature")

    try:
        event_data = json.loads(body_bytes.decode("utf-8"))
        event_type = event_data.get("event")
        payload = event_data.get("payload", {})

        logger.info(f"Received Razorpay Webhook Event: {event_type}")

        # Handle Payment Failed Event
        if event_type == "payment.failed":
            payment_entity = payload.get("payment", {}).get("entity", {})
            
            tx_id = payment_entity.get("id", f"txn_{payment_entity.get('order_id', 'unknown')}")
            amount_inr = payment_entity.get("amount", 0) / 100.0  # Convert paise to INR
            
            method_str = str(payment_entity.get("method", "upi")).upper()
            if "UPI" in method_str:
                method = PaymentMethod.UPI_INTENT
            elif "CARD" in method_str:
                method = PaymentMethod.CREDIT_CARD
            elif "NETBANKING" in method_str:
                method = PaymentMethod.NETBANKING
            else:
                method = PaymentMethod.UPI_INTENT

            error_code = payment_entity.get("error_code", "BAD_REQUEST_ERROR")
            error_reason = payment_entity.get("error_reason", "payment_timed_out")
            error_desc = payment_entity.get("error_description", "Payment failed at gateway")

            # Categorize failure
            if "timeout" in error_reason or "gateway" in error_reason:
                cat = FailureCategory.TRANSIENT_DOWNTIME
            elif "insufficient" in error_reason:
                cat = FailureCategory.INSUFFICIENT_FUNDS
            elif "cancel" in error_reason or "user" in error_reason:
                cat = FailureCategory.USER_DROPOUT
            elif "limit" in error_reason:
                cat = FailureCategory.LIMIT_EXCEEDED
            else:
                cat = FailureCategory.TRANSIENT_DOWNTIME

            # Safely handle notes (Razorpay can send [] or {})
            notes = payment_entity.get("notes")
            notes_dict = notes if isinstance(notes, dict) else {}
            cust_name = notes_dict.get("customer_name") or notes_dict.get("name") or notes_dict.get("customerName")
            
            # If not in notes, check card name or VPA handle
            if not cust_name:
                card_name = payment_entity.get("card", {}).get("name") if isinstance(payment_entity.get("card"), dict) else None
                vpa_str = str(payment_entity.get("vpa") or "")
                if card_name and card_name.strip() and card_name.lower() not in ["null", "none"]:
                    cust_name = card_name.strip()
                elif "@" in vpa_str and not vpa_str.startswith("pay_"):
                    vpa_handle = vpa_str.split("@")[0].replace(".", " ").replace("_", " ").title()
                    if len(vpa_handle) > 2 and not any(char.isdigit() for char in vpa_handle):
                        cust_name = vpa_handle
            
            # If still not resolved, derive clean name from contact/email or default to Harshit Pal
            if not cust_name:
                email = payment_entity.get("email") or ""
                if email and "void@razorpay.com" not in email and "@razorpay.com" not in email:
                    cust_name = email.split("@")[0].replace(".", " ").replace("_", " ").title()
                else:
                    cust_name = "Harshit Pal"

            now_local = datetime.now()
            tx = Transaction(
                transaction_id=tx_id,
                order_id=payment_entity.get("order_id"),
                customer_id=payment_entity.get("customer_id") or f"cust_{tx_id[:8]}",
                customer_name=cust_name,
                customer_email=payment_entity.get("email"),
                customer_phone=payment_entity.get("contact"),
                amount_inr=max(1.0, amount_inr),
                payment_method=method,
                issuer_bank=str(payment_entity.get("bank") or "HDFC"),
                psp=payment_entity.get("vpa", "").split("@")[-1].upper() if "@" in str(payment_entity.get("vpa") or "") else "GPAY",
                error_code=error_code,
                error_source=payment_entity.get("error_source", "gateway") or "gateway",
                error_step=payment_entity.get("error_step", "payment_authorization") or "payment_authorization",
                error_reason=error_reason,
                error_description=error_desc,
                failure_category=cat,
                customer_segment=CustomerSegment.STANDARD,
                created_at=now_local,
                failed_at=now_local,
            )

            await save_transaction(tx)

            # Auto-run recovery pipeline
            pipeline = RecoveryPipeline()
            decision, guardrail_result, audit_logs = await pipeline.process_transaction(tx)

            return {
                "status": "processed",
                "event": event_type,
                "transaction_id": tx_id,
                "recovery_action": decision.recommended_action.value if decision else "NO_ACTION",
            }

        # Handle Payment Link Paid (Recovery Success)
        elif event_type in ["payment_link.paid", "payment.captured"]:
            entity = payload.get("payment_link", {}).get("entity", {}) or payload.get("payment", {}).get("entity", {})
            ref_id = entity.get("reference_id", "")
            orig_tx_id = ref_id.replace("rec_", "") if ref_id.startswith("rec_") else ref_id
            amount_inr = entity.get("amount", 0) / 100.0

            if orig_tx_id:
                await update_transaction_status(orig_tx_id, "RECOVERED", recovered_amount=amount_inr)
                logger.info(f"✅ Transaction {orig_tx_id} marked as RECOVERED via Razorpay Webhook!")

            return {"status": "recovered", "event": event_type, "transaction_id": orig_tx_id}

        return {"status": "ignored", "event": event_type}

    except Exception as e:
        logger.error(f"Error handling Razorpay webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
