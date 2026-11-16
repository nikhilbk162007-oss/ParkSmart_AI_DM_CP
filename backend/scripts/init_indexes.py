import sys
from pymongo import MongoClient
from app.core.config import settings
from app.db.indexes import ensure_parking_indexes


def init_indexes():
    """
    Idempotent database index migration script.
    Can safely be executed repeatedly against MongoDB without errors.
    """
    print("Connecting to the configured MongoDB server.")
    client = MongoClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS
    )
    try:
        # Check connection
        client.admin.command("ping")
        db = client[settings.MONGODB_DB_NAME]
        print(f"Connected to database: {settings.MONGODB_DB_NAME}")

        print("Applying index migrations...")
        ensure_parking_indexes(db)
        print("Index migrations applied successfully.")

        for collection_name in ("parking", "users", "revoked_tokens"):
            indexes = db[collection_name].index_information()
            print(f"Current indexes on '{collection_name}' collection:")
            for idx_name, idx_info in indexes.items():
                print(f" - {idx_name}: {idx_info['key']}")

    except Exception as e:
        print(f"Failed to run index migration ({type(e).__name__}).")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    init_indexes()
