"""
app/routers/statements.py – PDF upload endpoint + transaction listing.

Endpoints:
  POST /statements/upload         → Upload PDF, parse, insert → UploadResult
  GET  /statements/transactions   → Paginated transaction list with filters
"""
import logging
from datetime import datetime
from typing import Annotated, Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status,
)
from pydantic import BaseModel

from app.models.transaction import TransactionResponse, UploadResult
from app.models.user import UserResponse
from app.parsers import PARSER_REGISTRY
from app.parsers.detector import detect_bank
from app.routers.auth import get_current_user
from app.services.transaction_service import (
    bulk_insert_transactions, get_transactions,
    update_transaction, delete_transaction,
)
from app.services.ml_service import ml_service
from app.utils.pdf_decrypt import decrypt_if_needed
from app.routers.uploads import save_upload_record

import pdfplumber
import io

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/statements", tags=["Statements"])

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_FILE_SIZE = 10 * 1024 * 1024   # 10 MB


# ── Debug endpoint (diagnose PDF without needing the file system) ──────────────
@router.post("/debug-pdf", summary="Diagnose what pdfplumber extracts from a PDF")
async def debug_pdf(file: UploadFile = File(...)):
    """
    Upload any PDF — returns a JSON report of:
      - How many pages
      - How many tables found per page (default & text strategy)
      - First 3 rows of each table
      - Raw text excerpt per page
    Use this to debug why a bank statement isn't parsing.
    """
    content = await file.read()
    if not content.startswith(b"%PDF"):
        raise HTTPException(422, "Not a valid PDF")

    report = {"filename": file.filename, "pages": []}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for pg_num, page in enumerate(pdf.pages, 1):
            page_info = {"page": pg_num, "strategies": {}}

            # Default (line) strategy
            tables_default = page.extract_tables() or []
            page_info["strategies"]["lines"] = {
                "table_count": len(tables_default),
                "row_counts": [len(t) for t in tables_default],
                "first_tables": [
                    {"col_count": len(t[0]) if t else 0, "rows": t[:3]}
                    for t in tables_default[:2]
                ],
            }

            # Text strategy
            try:
                tables_text = page.extract_tables({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                }) or []
            except Exception as e:
                tables_text = []
                page_info["strategies"]["text_error"] = str(e)

            page_info["strategies"]["text"] = {
                "table_count": len(tables_text),
                "row_counts": [len(t) for t in tables_text],
                "first_tables": [
                    {"col_count": len(t[0]) if t else 0, "rows": t[:3]}
                    for t in tables_text[:2]
                ],
            }

            # Raw text excerpt
            raw = page.extract_text() or ""
            page_info["raw_text_lines"] = raw.split("\n")[:10]
            report["pages"].append(page_info)

    return report



# ── Helpers ───────────────────────────────────────────────────────────────────
def _validate_pdf(file: UploadFile, content: bytes) -> None:
    """Raise HTTPException on bad file type or size."""
    # Extension check
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only .pdf files are accepted.",
        )
    # Size check
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds 10 MB limit ({len(content) / 1024 / 1024:.1f} MB received).",
        )
    # Magic bytes check (PDF starts with %PDF)
    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file does not appear to be a valid PDF.",
        )


def _extract_full_text(content: bytes) -> str:
    """Extract all text from a PDF for bank detection."""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages_text = [p.extract_text() or "" for p in pdf.pages[:3]]
            return "\n".join(pages_text)
    except Exception:
        return ""


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post(
    "/upload",
    response_model=UploadResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a bank PDF statement and parse transactions",
)
async def upload_statement(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    file: UploadFile = File(..., description="Bank statement PDF (max 10 MB)"),
    bank: Optional[str] = Query(
        default=None,
        description="Force a specific bank parser: sbi | hdfc | icici | bob. "
                    "Leave blank to auto-detect.",
    ),
    password: Optional[str] = Form(
        default=None,
        description=(
            "PDF password (if statement is password-protected). "
            "Most Indian banks use date of birth in DDMMYYYY format — e.g. '01011990'."
        ),
    ),
):
    """
    Upload a PDF bank statement (password-protected or plain).

    1. Validates file (extension, size, magic bytes).
    2. Decrypts if password-protected (pass `password` form field).
    3. Auto-detects or uses supplied `bank` parameter.
    4. Runs the appropriate parser.
    5. Bulk-inserts transactions (skips duplicates).
    6. Returns UploadResult with counts.
    """
    content = await file.read()
    _validate_pdf(file, content)

    # ── Decrypt if password-protected ────────────────────────────────────────
    try:
        content = decrypt_if_needed(content, password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # ── Bank detection ────────────────────────────────────────────────────────
    bank_id = bank.lower().strip() if bank else None
    if bank_id and bank_id not in PARSER_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown bank '{bank_id}'. Choose from: {list(PARSER_REGISTRY)}",
        )

    if not bank_id:
        text = _extract_full_text(content)
        bank_id = detect_bank(text)
        logger.info("Auto-detected bank: %s (file=%s)", bank_id, file.filename)

    if bank_id == "unknown" or bank_id not in PARSER_REGISTRY:
        # Log first 500 chars to help debug detection
        logger.warning(
            "Bank not detected for file '%s'. PDF text sample: %s",
            file.filename, text[:500] if text else "(no text extracted)",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Could not detect the bank from this PDF. "
                "Please select the bank manually from the dropdown: "
                "sbi | hdfc | icici | bob | idbi | kotak | cbi"
            ),
        )

    # ── Parse ─────────────────────────────────────────────────────────────────
    ParserClass = PARSER_REGISTRY[bank_id]
    parser = ParserClass()
    try:
        transactions = parser.parse(content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"PDF parsing failed: {exc}",
        )

    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"No transactions found in this {bank_id.upper()} PDF. "
                "Possible reasons: (1) scanned/image PDF — only text-based PDFs are supported, "
                "(2) wrong bank selected — try auto-detect or select the correct bank, "
                "(3) the statement format may differ from the supported layout."
            ),
        )

    # ── ML categorisation (batch, single vectoriser call) ─────────────────────
    txn_inputs = [
        {
            "merchant":    t.merchant,
            "amount":      t.amount,
            "hour":        t.date.hour,
            "day_of_week": t.date.weekday(),
        }
        for t in transactions
    ]
    ml_predictions    = ml_service.categorize_batch(txn_inputs)
    categorized_count = 0
    for txn, pred in zip(transactions, ml_predictions):
        if pred["category"] != "Uncategorized":
            txn.category  = pred["category"]
            categorized_count += 1

    # ── Anomaly pre-check on upload batch (no extra DB round-trip) ────────────
    anomaly_count = 0
    if ml_service.anomaly_ready and txn_inputs:
        try:
            import numpy as _np
            X_raw    = _np.array(
                [[t["amount"], t["hour"], t["day_of_week"]] for t in txn_inputs],
                dtype=_np.float32,
            )
            X_scaled = ml_service.scaler.transform(X_raw)
            labels   = ml_service.detector.predict(X_scaled)
            anomaly_count = int((_np.array(labels) == -1).sum())
        except Exception as _exc:
            logger.warning("Anomaly pre-check failed during upload: %s", _exc)

    # ── Bulk insert (with ML-enriched categories) ─────────────────────────────
    result = await bulk_insert_transactions(
        user_id=current_user.id,
        transactions=transactions,
    )
    logger.info(
        "Upload complete – user=%s inserted=%d categorized=%d anomalies=%d",
        current_user.id, result.inserted, categorized_count, anomaly_count,
    )

    # ── Save upload record to history ─────────────────────────────────────────
    await save_upload_record(
        user_id=current_user.id,
        bank=result.bank,
        filename=file.filename or "unknown.pdf",
        total_rows=result.total_rows,
        inserted=result.inserted,
        duplicates=result.duplicates,
        errors=result.errors,
    )

    return result



@router.get(
    "/transactions",
    response_model=dict,
    summary="List parsed transactions (paginated)",
)
async def list_transactions(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    bank: Optional[str]       = Query(None, description="Filter by bank"),
    type: Optional[str]       = Query(None, description="debit | credit"),
    date_from: Optional[datetime] = Query(None, description="ISO date lower bound"),
    date_to:   Optional[datetime] = Query(None, description="ISO date upper bound"),
    page:      int = Query(1,  ge=1,   description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Results per page"),
):
    """Return paginated transactions for the authenticated user."""
    txns, total = await get_transactions(
        user_id=current_user.id,
        bank=bank,
        txn_type=type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return {
        "page":       page,
        "page_size":  page_size,
        "total":      total,
        "data":       [t.model_dump() for t in txns],
    }


# ── Update a single transaction ────────────────────────────────────────────────
class _TransactionUpdate(BaseModel):
    merchant: Optional[str] = None
    category: Optional[str] = None
    amount:   Optional[float] = None
    type:     Optional[str] = None


@router.put(
    "/transactions/{txn_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Edit merchant / category / amount / type of a transaction",
)
async def update_transaction_route(
    txn_id: str,
    body: _TransactionUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Update editable fields on a transaction owned by the current user.

    When a category is changed and the transaction has a upi_id, ALL other
    transactions for the same upi sender are also updated (propagation).

    Returns the updated transaction plus:
      - matched_count: total transactions updated (1 + propagated)
      - upi_id: the UPI sender ID used for propagation (if any)
    """
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = await update_transaction(
        user_id=current_user.id,
        txn_id=txn_id,
        updates=updates,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{txn_id}' not found.",
        )
    # result is a dict: { transaction: TransactionResponse, matched_count: int, upi_id: str|None }
    txn_data = result["transaction"].model_dump()
    txn_data["matched_count"] = result.get("matched_count", 1)
    txn_data["upi_id"] = result.get("upi_id")
    return txn_data


# ── Delete a single transaction ────────────────────────────────────────────────
@router.delete(
    "/transactions/{txn_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a transaction",
)
async def delete_transaction_route(
    txn_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Permanently delete a transaction owned by the current user."""
    deleted = await delete_transaction(
        user_id=current_user.id,
        txn_id=txn_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{txn_id}' not found.",
        )
    return {"deleted": True, "id": txn_id}
