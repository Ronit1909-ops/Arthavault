"""
app/services/auth_service.py – Auth business logic (Google OAuth + DB)
"""
import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from app.database import get_database
from app.models.user import UserResponse, UserUpsert

logger = logging.getLogger(__name__)


async def get_or_create_user(google_profile: dict[str, Any]) -> UserResponse:
    """
    Given the raw profile dict returned by Google's UserInfo endpoint,
    upsert the user document in MongoDB and return a UserResponse.

    google_profile keys expected:
        sub, email, name, picture
    """
    db = get_database()
    users = db["users"]

    google_id: str = google_profile["sub"]
    email: str     = google_profile["email"]
    name: str      = google_profile.get("name", email.split("@")[0])
    picture: str | None = google_profile.get("picture")

    now = datetime.now(timezone.utc)

    # Upsert: if google_id exists → update name/picture/updated_at
    #         if not → insert full document
    doc = await users.find_one_and_update(
        {"google_id": google_id},
        {
            "$set": {
                "email":      email,
                "name":       name,
                "picture":    picture,
                "updated_at": now,
            },
            "$setOnInsert": {
                "google_id":   google_id,
                "created_at":  now,
                "preferences": {
                    "currency":               "INR",
                    "timezone":               "Asia/Kolkata",
                    "notifications_enabled":  True,
                    "monthly_budget":         None,
                },
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    logger.info("Upserted user google_id=%s  _id=%s", google_id, doc["_id"])
    return UserResponse.from_document(doc)


async def get_user_by_id(user_id: str) -> UserResponse | None:
    """Fetch a user by MongoDB ObjectId string. Returns None if not found."""
    db = get_database()
    users = db["users"]

    try:
        oid = ObjectId(user_id)
    except Exception:
        return None

    doc = await users.find_one({"_id": oid})
    if doc is None:
        return None
    return UserResponse.from_document(doc)
