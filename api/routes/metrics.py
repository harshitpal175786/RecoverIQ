from fastapi import APIRouter, HTTPException
from schemas.metrics import RecoveryMetrics, ComparisonReport
from data.db import get_all_transactions, get_recovery_attempts
from evaluation.runner import EvaluationRunner
from evaluation.metrics import compute_metrics

router = APIRouter(tags=["metrics"])

@router.get("/metrics", response_model=RecoveryMetrics)
async def get_metrics_route():
    try:
        transactions = await get_all_transactions()
        attempts = await get_recovery_attempts()
        return compute_metrics(transactions, attempts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compare", response_model=ComparisonReport)
async def compare_evaluation():
    try:
        transactions = await get_all_transactions()
        runner = EvaluationRunner()
        report = runner.run_comparison(transactions)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
