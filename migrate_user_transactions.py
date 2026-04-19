"""
One-time migration: move all transactions from old_user_id to current_user_id.
Run: .venv\Scripts\python.exe migrate_user_transactions.py
"""
import asyncio, sys
sys.path.insert(0, ".")

OLD_USER_ID = "69e3eafd28176e9f8d5f0adc"   # ronitpal2003@gmail.com
NEW_USER_ID = "69cf95263171f4f6a018df33"   # devildec1011@gmail.com (current login)


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
