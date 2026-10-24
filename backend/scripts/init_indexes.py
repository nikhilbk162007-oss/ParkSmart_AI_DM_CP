import sys
from pymongo import MongoClient
from app.core.config import settings
from app.db.indexes import ensure_parking_indexes


def init_indexes():
    """
    Idempotent database index migration script.
    Can safely be executed repeatedly against MongoDB without errors.
    """
    print(f"Connecting to MongoDB at: {settings.MONGODB_URI}")
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
        print("✅ Index migrations applied successfully.")

        # List existing indexes for verification
        indexes = db.parking.index_information()
        print("Current indexes on 'parking' collection:")
        for idx_name, idx_info in indexes.items():
            print(f" - {idx_name}: {idx_info['key']}")

    except Exception as e:
        print(f"❌ Failed to run index migration: {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    init_indexes()
