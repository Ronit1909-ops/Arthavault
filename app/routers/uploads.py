"""
app/routers/uploads.py – Upload history endpoints.

Endpoints:
  GET  /uploads/history          → Return all upload records for the current user
  POST /uploads/history          → Internal: save an upload record (called by statements router)
"""
import logging
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.database import get_database
from app.models.user import UserResponse
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/uploads", tags=["Uploads"])

_COL = "upload_history"


# ── Schemas ───────────────────────────────────────────────────────────────────

class UploadHistoryItem(BaseModel):
    id: str
    bank: str
    filename: str
    total_rows: int
    inserted: int
    duplicates: int
    errors: int
    uploaded_at: str      # ISO string


class UploadHistoryResponse(BaseModel):
    history: list[UploadHistoryItem]
    count: int


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get(
    "/history",
    response_model=UploadHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get upload history for the current user",
)
async def get_upload_history(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Return all statement uploads made by the current user, newest first."""
    db  = get_database()
    col = db[_COL]
    docs = await col.find(
        {"user_id": current_user.id},
    ).sort("uploaded_at", -1).to_list(length=50)

    items = [
        UploadHistoryItem(
            id=str(d["_id"]),
            bank=d.get("bank", "unknown"),
            filename=d.get("filename", ""),
            total_rows=d.get("total_rows", 0),
            inserted=d.get("inserted", 0),
            duplicates=d.get("duplicates", 0),
            errors=d.get("errors", 0),
            uploaded_at=d["uploaded_at"].isoformat() if hasattr(d["uploaded_at"], "isoformat") else str(d["uploaded_at"]),
        )
        for d in docs
    ]
    return UploadHistoryResponse(history=items, count=len(items))


# ── Internal helper (called from statements router, not exposed directly) ──────

async def save_upload_record(
    user_id: str,
    bank: str,
    filename: str,
    total_rows: int,
    inserted: int,
    duplicates: int,
    errors: int,
) -> str:
    """Insert an upload history record and return its string ID."""
    db  = get_database()
    col = db[_COL]
    doc = {
        "user_id":    user_id,
        "bank":       bank,
        "filename":   filename,
        "total_rows": total_rows,
        "inserted":   inserted,
        "duplicates": duplicates,
        "errors":     errors,
        "uploaded_at": datetime.now(timezone.utc),
    }
    result = await col.insert_one(doc)
    logger.info("Saved upload history id=%s user=%s bank=%s inserted=%d",
                result.inserted_id, user_id, bank, inserted)
    return str(result.inserted_id)
