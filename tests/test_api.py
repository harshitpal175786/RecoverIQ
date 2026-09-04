"""Automated tests for RecoverIQ API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify system health diagnostics endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Verify live financial metrics endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "recovery_rate_pct" in data
        assert "total_transactions" in data
        assert "recovered_amount_inr" in data


@pytest.mark.asyncio
async def test_compare_benchmark_endpoint():
    """Verify ROI comparison benchmark endpoint against baseline."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/compare?count=5")
        assert response.status_code == 200
        data = response.json()
        assert "baseline" in data
        assert "recoveriq" in data
        assert "recovery_rate_uplift_pct" in data
        assert "revenue_uplift_inr" in data


@pytest.mark.asyncio
async def test_transactions_endpoint():
    """Verify transactions ledger listing endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/transactions?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0


@pytest.mark.asyncio
async def test_webhook_get_endpoint():
    """Verify webhook receiver ping endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/webhooks/razorpay")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "active"


@pytest.mark.asyncio
async def test_copilot_chat_endpoint():
    """Verify AI Copilot chat conversational query endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={"message": "What is our current recovery win rate and total revenue won back?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 10
        assert "suggested_actions" in data
