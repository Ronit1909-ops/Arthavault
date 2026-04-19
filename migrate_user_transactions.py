"""
One-time migration: move all transactions from old_user_id to current_user_id.
Run: .venv\Scripts\python.exe migrate_user_transactions.py
"""
import os

# Set these via environment variables or pass as CLI args before running:
#   OLD_USER_ID = the old MongoDB _id string of the user whose transactions to migrate
#   NEW_USER_ID = the new MongoDB _id string to reassign transactions to
OLD_USER_ID = os.environ.get("OLD_USER_ID", "")   # export OLD_USER_ID=<your-old-id>
NEW_USER_ID = os.environ.get("NEW_USER_ID", "")   # export NEW_USER_ID=<your-new-id>


async def main():
    from app.database import connect_db, get_database
    await connect_db()
    db = get_database()
    col = db["transactions"]

    # Confirm counts before migration
    old_count = await col.count_documents({"user_id": OLD_USER_ID})
    new_count = await col.count_documents({"user_id": NEW_USER_ID})
    print(f"Before migration:")
    print(f"  Old user ({OLD_USER_ID}): {old_count} txns")
    print(f"  New user ({NEW_USER_ID}): {new_count} txns")

    if old_count == 0:
        print("Nothing to migrate.")
        return

    print(f"\nMigrating {old_count} transactions to new user...")
    result = await col.update_many(
        {"user_id": OLD_USER_ID},
        {"$set": {"user_id": NEW_USER_ID}},
    )
    print(f"Modified: {result.modified_count}")

    # Confirm after
    old_after = await col.count_documents({"user_id": OLD_USER_ID})
    new_after  = await col.count_documents({"user_id": NEW_USER_ID})
    print(f"\nAfter migration:")
    print(f"  Old user ({OLD_USER_ID}): {old_after} txns")
    print(f"  New user ({NEW_USER_ID}): {new_after} txns")
    print("\nDone! Refresh the Insights page in the browser.")

asyncio.run(main())
