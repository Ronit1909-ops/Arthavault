"""
app/services/transaction_service.py – Bulk insert + dedup + query logic.

Dedup strategy:
  Each transaction gets a SHA-256 hash of:
      date (ISO) + upi_ref (or description first-40) + str(amount)

  MongoDB index on `hash` is UNIQUE.
  Bulk write uses ordered=False + DuplicateKeyError filtering, so a batch
  of 500+ rows processes at maximum write speed even with duplicates.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from pymongo import InsertOne, ASCENDING, DESCENDING
from pymongo.errors import BulkWriteError

from app.database import get_database
from app.models.transaction import (
    BankName, TransactionCreate, TransactionResponse, TransactionType, UploadResult,
)

logger = logging.getLogger(__name__)

_COL = "transactions"


# ── Hash helper ───────────────────────────────────────────────────────────────
def _make_hash(date: datetime, upi_ref: Optional[str], description: str, amount: float) -> str:
    """SHA-256 of canonical fields → hex string used as dedup key."""
    key = "|".join([
        date.strftime("%Y-%m-%d"),
        (upi_ref or description[:40]).strip().upper(),
        f"{amount:.2f}",
    ])
    return hashlib.sha256(key.encode()).hexdigest()


# ── Ensure indexes (called from database.py startup too, but safe to repeat) ──
async def ensure_transaction_indexes() -> None:
    db = get_database()
    col = db[_COL]
    from pymongo import IndexModel
    await col.create_indexes([
        IndexModel([("hash", ASCENDING)],                unique=True, name="hash_unique"),
        IndexModel([("user_id", ASCENDING), ("date", DESCENDING)], name="user_date"),
        IndexModel([("user_id", ASCENDING), ("bank", ASCENDING)],  name="user_bank"),
    ])


# ── Bulk insert ───────────────────────────────────────────────────────────────
async def bulk_insert_transactions(
    user_id: str,
    transactions: list[TransactionCreate],
) -> UploadResult:
    """
    Insert up to 500+ transactions in a single bulk operation.
    Duplicate hashes are silently skipped (counted separately).
    Returns an UploadResult summary.
    """
    if not transactions:
        return UploadResult(bank="unknown", total_rows=0, inserted=0, duplicates=0, errors=0)

    db   = get_database()
    col  = db[_COL]
    now  = datetime.now(timezone.utc)

    requests: list[InsertOne] = []
    bank_name = transactions[0].bank if transactions else BankName.unknown
    error_count = 0

    for txn in transactions:
        try:
            h = _make_hash(txn.date, txn.upi_ref, txn.description, txn.amount)
            doc = {
                "user_id":     user_id,
                "date":        txn.date,
                "description": txn.description,
                "merchant":    txn.merchant,
                "amount":      txn.amount,
                "type":        txn.type.value if hasattr(txn.type, "value") else txn.type,
                "upi_ref":     txn.upi_ref,
                "category":    txn.category,
                "source":      "pdf",
                "bank":        txn.bank.value if hasattr(txn.bank, "value") else txn.bank,
                "balance":     txn.balance,
                "hash":        h,
                "created_at":  now,
            }
            requests.append(InsertOne(doc))
        except Exception as exc:
            logger.warning("Pre-insert build error: %s | txn=%s", exc, txn)
            error_count += 1

    inserted = 0
    duplicates = 0

    if requests:
        try:
            result = await col.bulk_write(requests, ordered=False)
            inserted = result.inserted_count
        except BulkWriteError as bwe:
            # Separate duplicate-key errors (code 11000) from real errors
            for err in bwe.details.get("writeErrors", []):
                if err.get("code") == 11000:
                    duplicates += 1
                else:
                    error_count += 1
                    logger.error("Bulk write error: %s", err)
            inserted = bwe.details.get("nInserted", 0)

    logger.info(
        "Bulk insert complete: inserted=%d duplicates=%d errors=%d",
        inserted, duplicates, error_count,
    )
    return UploadResult(
        bank=bank_name.value if hasattr(bank_name, "value") else str(bank_name),
        total_rows=len(transactions),
        inserted=inserted,
        duplicates=duplicates,
        errors=error_count,
    )


# ── Query ─────────────────────────────────────────────────────────────────────
async def get_transactions(
    user_id: str,
    bank: Optional[str] = None,
    txn_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[TransactionResponse], int]:
    """
    Paginated transaction query with optional filters.
    Returns (transactions, total_count).
    """
    db  = get_database()
    col = db[_COL]

    query: dict = {"user_id": user_id}
    if bank:
        query["bank"] = bank
    if txn_type:
        query["type"] = txn_type
    if date_from or date_to:
        query["date"] = {}
        if date_from:
            query["date"]["$gte"] = date_from
        if date_to:
            query["date"]["$lte"] = date_to

    skip  = (page - 1) * page_size
    total = await col.count_documents(query)
    docs  = await col.find(query).sort("date", DESCENDING).skip(skip).limit(page_size).to_list(page_size)

    return [TransactionResponse.from_document(d) for d in docs], total


# ── Update ─────────────────────────────────────────────────────────────────────
async def update_transaction(
    user_id: str,
    txn_id: str,
    updates: dict,
) -> Optional[TransactionResponse]:
    """
    Patch editable fields (merchant, category, amount, type) on a transaction.
    Scoped to user_id so users can only update their own docs.
    Returns the updated TransactionResponse or None if not found.
    """
    from bson import ObjectId
    from bson.errors import InvalidId

    db  = get_database()
    col = db[_COL]

    try:
        oid = ObjectId(txn_id)
    except (InvalidId, Exception):
        return None

    # Allow only safe fields to be patched
    allowed = {"merchant", "category", "amount", "type"}
    patch = {k: v for k, v in updates.items() if k in allowed}
    if not patch:
        return None

    result = await col.find_one_and_update(
        {"_id": oid, "user_id": user_id},
        {"$set": patch},
        return_document=True,   # return the updated document
    )
    if result is None:
        return None
    return TransactionResponse.from_document(result)


# ── Delete ─────────────────────────────────────────────────────────────────────
async def delete_transaction(user_id: str, txn_id: str) -> bool:
    """
    Delete a single transaction by _id, scoped to user_id.
    Returns True if deleted, False if not found.
    """
    from bson import ObjectId
    from bson.errors import InvalidId

    db  = get_database()
    col = db[_COL]

    try:
        oid = ObjectId(txn_id)
    except (InvalidId, Exception):
        return False

    result = await col.delete_one({"_id": oid, "user_id": user_id})
    return result.deleted_count == 1
