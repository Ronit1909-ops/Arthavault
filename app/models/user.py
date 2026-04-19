"""
app/models/user.py – User document schema (Pydantic v2 + MongoDB)
"""
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field


# ── Reusable sub-model ───────────────────────────────────────────────────────
class UserPreferences(BaseModel):
    currency: str = "INR"
    timezone: str = "Asia/Kolkata"
    notifications_enabled: bool = True
    monthly_budget: Optional[float] = None  # in INR


# ── Main document model ──────────────────────────────────────────────────────
class UserDocument(BaseModel):
    """Mirrors the MongoDB users collection document."""

    # MongoDB stores _id as ObjectId; we expose it as a string alias.
    id: Optional[str] = Field(default=None, alias="_id")

    google_id: str = Field(..., description="Google sub (subject) identifier")
    email: EmailStr = Field(..., description="Primary Google account email")
    name: str = Field(..., description="Display name from Google profile")
    picture: Optional[str] = Field(default=None, description="Google avatar URL")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    preferences: UserPreferences = Field(default_factory=UserPreferences)

    model_config = {
        # Allow population by field name OR alias (_id)
        "populate_by_name": True,
        # Needed so datetime serialises correctly
        "json_encoders": {datetime: lambda v: v.isoformat()},
    }


# ── API response shape (safe – no internal fields) ───────────────────────────
class UserResponse(BaseModel):
    id: str
    google_id: str
    email: str
    name: str
    picture: Optional[str]
    created_at: datetime
    preferences: UserPreferences

    @classmethod
    def from_document(cls, doc: dict[str, Any]) -> "UserResponse":
        return cls(
            id=str(doc["_id"]),
            google_id=doc["google_id"],
            email=doc["email"],
            name=doc["name"],
            picture=doc.get("picture"),
            created_at=doc["created_at"],
            preferences=UserPreferences(**doc.get("preferences", {})),
        )


# ── Upsert / create payload ───────────────────────────────────────────────────
class UserUpsert(BaseModel):
    google_id: str
    email: str
    name: str
    picture: Optional[str] = None
