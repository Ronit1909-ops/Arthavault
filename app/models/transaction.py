"""
app/models/transaction.py – Transaction document schema for MongoDB
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    debit  = "debit"
    credit = "credit"


class TransactionSource(str, Enum):
    pdf    = "pdf"
    manual = "manual"


class BankName(str, Enum):
    sbi   = "sbi"
    hdfc  = "hdfc"
    icici = "icici"
    bob   = "bob"
    idbi  = "idbi"
    kotak = "kotak"
    cbi   = "cbi"
    unknown = "unknown"


# ── MongoDB document ──────────────────────────────────────────────────────────
class TransactionDocument(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")

    user_id:     str   = Field(..., description="Owner's MongoDB user _id")
    date:        datetime
    description: str   = Field(..., description="Raw row text from PDF")
    merchant:    str   = Field(default="Unknown", description="Extracted merchant name")
    amount:      float = Field(..., ge=0, description="Absolute transaction amount (INR)")
    type:        TransactionType
    upi_ref:     Optional[str]  = None
    category:    str            = "Uncategorized"
    source:      TransactionSource = TransactionSource.pdf
    bank:        BankName       = BankName.unknown
    balance:     Optional[float] = None

    # SHA-256 of (date_iso + upi_ref + str(amount)) – used for dedup
    hash:        str = Field(..., description="Dedup hash")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
        "json_encoders": {datetime: lambda v: v.isoformat()},
    }


# ── Create payload (from parser) ─────────────────────────────────────────────
class TransactionCreate(BaseModel):
    """Filled in by each bank parser; user_id and hash are added by the service."""
    date:        datetime
    description: str
    merchant:    str      = "Unknown"
    amount:      float
    type:        TransactionType
    upi_ref:     Optional[str]  = None
    category:    str            = "Uncategorized"
    bank:        BankName       = BankName.unknown
    balance:     Optional[float] = None


# ── API response ──────────────────────────────────────────────────────────────
class TransactionResponse(BaseModel):
    id:          str
    user_id:     str
    date:        datetime
    description: str
    merchant:    str
    amount:      float
    type:        str
    upi_ref:     Optional[str]
    category:    str
    bank:        str
    balance:     Optional[float]
    created_at:  datetime

    @classmethod
    def from_document(cls, doc: dict[str, Any]) -> "TransactionResponse":
        return cls(
            id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            date=doc["date"],
            description=doc["description"],
            merchant=doc.get("merchant", "Unknown"),
            amount=doc["amount"],
            type=doc["type"],
            upi_ref=doc.get("upi_ref"),
            category=doc.get("category", "Uncategorized"),
            bank=doc.get("bank", "unknown"),
            balance=doc.get("balance"),
            created_at=doc["created_at"],
        )


# ── Upload response ───────────────────────────────────────────────────────────
class UploadResult(BaseModel):
    bank:       str
    total_rows: int
    inserted:   int
    duplicates: int
    errors:     int
