from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
import uuid
from data.generator import generate_batch
from data.db import save_transactions_batch

router = APIRouter(tags=["seed"])

class SeedResponse(BaseModel):
    batch_id: str
    count: int
    total_amount_inr: float
    message: str

@router.post("/seed", response_model=SeedResponse)
async def seed_data(
    count: int = Query(500, description="Number of transactions to generate"),
    seed: int = Query(42, description="Random seed")
):
    try:
        transactions = generate_batch(count=count, seed=seed)
        await save_transactions_batch(transactions)
        
        batch_id = str(uuid.uuid4())
        total_amount = sum(t.amount_inr for t in transactions)
        
        return SeedResponse(
            batch_id=batch_id,
            count=len(transactions),
            total_amount_inr=total_amount,
            message="Data seeded successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
