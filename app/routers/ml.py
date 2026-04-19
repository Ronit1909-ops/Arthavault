"""
app/routers/ml.py – ML inference endpoints.

Endpoints
---------
POST /ml/categorize              → Single transaction categorisation
POST /ml/categorize-batch        → Batch transaction categorisation
GET  /ml/forecast/{user_id}      → Prophet spending forecast
GET  /ml/anomalies/{user_id}     → Isolation Forest anomaly detection
GET  /ml/health                  → Model health check

curl examples
-------------
# Single categorise
curl -X POST http://localhost:8000/ml/categorize \\
     -H "Content-Type: application/json" \\
     -d '{"merchant":"ZOMATO","amount":450,"hour":20,"day_of_week":5}'

# Batch categorise
curl -X POST http://localhost:8000/ml/categorize-batch \\
     -H "Content-Type: application/json" \\
     -d '{"transactions":[{"merchant":"ZOMATO","amount":450,"hour":20,"day_of_week":5},{"merchant":"AMAZON","amount":1200}]}'

# Forecast (requires valid JWT cookie)
curl http://localhost:8000/ml/forecast/USER_ID?days=30

# Anomalies
curl http://localhost:8000/ml/anomalies/USER_ID?days=30

# Health
curl http://localhost:8000/ml/health
"""
from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.database import get_database
from app.services.ml_service import ml_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml", tags=["ML"])


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic schemas
# ═══════════════════════════════════════════════════════════════════════════════

class TransactionInput(BaseModel):
    """Single transaction for categorisation."""
    merchant:    str         = Field(..., examples=["ZOMATO"])
    amount:      float       = Field(..., gt=0, examples=[450.0])
    hour:        int         = Field(default=12, ge=0, le=23, examples=[20])
    day_of_week: int         = Field(default=0,  ge=0, le=6,  examples=[5])


class CategoryPrediction(BaseModel):
    category:          str
    confidence:        float
    top_3_predictions: list[dict]


class BatchCategorizeRequest(BaseModel):
    transactions: list[TransactionInput] = Field(..., min_length=1)


class BatchCategorizeResponse(BaseModel):
    results: list[CategoryPrediction]
    count:   int


class ForecastRow(BaseModel):
    date:            str
    predicted_spend: float
    lower_bound:     float
    upper_bound:     float


class ForecastResponse(BaseModel):
    forecast:            list[ForecastRow]
    total_predicted:     float
    confidence_interval: str


class AnomalyItem(BaseModel):
    transaction_id: str
    merchant:       str
    amount:         float
    date:           str
    is_anomaly:     bool
    anomaly_score:  float
    explanation:    str


class AnomalyResponse(BaseModel):
    anomalies: list[AnomalyItem]
    count:     int


class MLHealthResponse(BaseModel):
    status:        str
    models_loaded: bool
    models:        dict[str, bool]


# ═══════════════════════════════════════════════════════════════════════════════
# Dependency helpers
# ═══════════════════════════════════════════════════════════════════════════════

def get_ml_service():
    """FastAPI dependency that returns the shared MLService singleton."""
    return ml_service


async def get_db():
    """FastAPI dependency that returns the Motor database handle."""
    return get_database()


# ═══════════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/categorize",
    response_model=CategoryPrediction,
    status_code=status.HTTP_200_OK,
    summary="Predict the spending category for a single transaction",
)
async def categorize_transaction(
    body: TransactionInput,
    svc=Depends(get_ml_service),
):
    """
    Use the XGBoost classifier + TF-IDF vectorizer to predict which spending
    category a transaction belongs to.

    curl example
    ------------
    curl -X POST http://localhost:8000/ml/categorize \\
         -H "Content-Type: application/json" \\
         -d '{"merchant":"ZOMATO","amount":450,"hour":20,"day_of_week":5}'
    """
    try:
        result = svc.categorize_transaction(
            merchant=body.merchant,
            amount=body.amount,
            hour=body.hour,
            day_of_week=body.day_of_week,
        )
        return CategoryPrediction(**result)
    except Exception as exc:
        logger.error("POST /ml/categorize error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Categorisation failed. See server logs for details.",
        )


@router.post(
    "/categorize-batch",
    response_model=BatchCategorizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch-predict categories for multiple transactions",
)
async def categorize_batch(
    body: BatchCategorizeRequest,
    svc=Depends(get_ml_service),
):
    """
    Vectorise all merchant names in a single pass (efficient for bulk imports).

    curl example
    ------------
    curl -X POST http://localhost:8000/ml/categorize-batch \\
         -H "Content-Type: application/json" \\
         -d '{"transactions":[{"merchant":"ZOMATO","amount":450},{"merchant":"AMAZON","amount":1200}]}'
    """
    if not body.transactions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="transactions list must not be empty.",
        )

    try:
        txn_dicts = [t.model_dump() for t in body.transactions]
        raw       = svc.categorize_batch(txn_dicts)
        results   = [CategoryPrediction(**r) for r in raw]
        return BatchCategorizeResponse(results=results, count=len(results))
    except Exception as exc:
        logger.error("POST /ml/categorize-batch error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch categorisation failed. See server logs for details.",
        )


@router.get(
    "/forecast/{user_id}",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Prophet spending forecast for a user",
)
async def forecast_spending(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of future days to forecast"),
    svc=Depends(get_ml_service),
    db=Depends(get_db),
):
    """
    Fetch the user's debit history from MongoDB and generate a day-by-day
    spending forecast using the pre-trained Prophet model.

    curl example
    ------------
    curl "http://localhost:8000/ml/forecast/USER_ID?days=30"
    """
    try:
        data = await svc.forecast_spending(user_id=user_id, days=days, db=db)
    except Exception as exc:
        logger.error("GET /ml/forecast/%s error: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Forecast generation failed. See server logs for details.",
        )

    # Only 404 when there is literally no forecast list (no transactions at all)
    if not data.get("forecast"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No transaction history found for user '{user_id}'.",
        )

    return ForecastResponse(**data)


@router.get(
    "/anomalies/{user_id}",
    response_model=AnomalyResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect anomalous transactions for a user",
)
async def detect_anomalies(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Look-back window in days"),
    svc=Depends(get_ml_service),
    db=Depends(get_db),
):
    """
    Run the Isolation Forest model on the user's recent debit transactions
    and return those flagged as anomalous with a human-readable explanation.

    curl example
    ------------
    curl "http://localhost:8000/ml/anomalies/USER_ID?days=30"
    """
    try:
        items = await svc.detect_anomalies(user_id=user_id, days=days, db=db)
    except Exception as exc:
        logger.error("GET /ml/anomalies/%s error: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Anomaly detection failed. See server logs for details.",
        )

    anomalies = [AnomalyItem(**item) for item in items]
    return AnomalyResponse(anomalies=anomalies, count=len(anomalies))


@router.get(
    "/health",
    response_model=MLHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="ML model health check",
)
async def ml_health(svc=Depends(get_ml_service)):
    """
    Returns which models are loaded and an overall readiness status.

    curl example
    ------------
    curl http://localhost:8000/ml/health
    """
    h = svc.health()
    return MLHealthResponse(
        status="ok" if h["models_loaded"] else "degraded",
        **h,
    )
