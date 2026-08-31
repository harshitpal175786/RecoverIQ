import httpx
import logging
from config import get_settings

logger = logging.getLogger(__name__)

class RazorpayExecutor:
    """Optional Razorpay Test Mode executor."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://api.razorpay.com/v1"
        self.auth = (self.settings.RAZORPAY_KEY_ID, self.settings.RAZORPAY_KEY_SECRET)
    
    async def create_payment_link(self, transaction, decision) -> dict:
        """Create a Razorpay Payment Link for recovery."""
        payload = {
            "amount": int(transaction.amount_inr * 100),
            "currency": "INR",
            "reference_id": f"rec_{transaction.transaction_id}",
            "description": "Payment Recovery",
            "customer": {
                "name": transaction.customer_id,
                "email": f"{transaction.customer_id}@example.com"
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/payment_links", json=payload, auth=self.auth)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to create payment link: {e}")
                return {}
    
    async def check_payment_status(self, payment_id: str) -> dict:
        """Check status of a payment."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/payments/{payment_id}", auth=self.auth)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to fetch payment status: {e}")
                return {}
    
    async def fetch_payment_link(self, link_id: str) -> dict:
        """Fetch payment link status."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/payment_links/{link_id}", auth=self.auth)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to fetch payment link: {e}")
                return {}
