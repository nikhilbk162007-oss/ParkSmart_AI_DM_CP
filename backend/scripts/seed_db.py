import sys
from pymongo import MongoClient
from app.core.config import settings
from app.db.indexes import ensure_parking_indexes
from app.repositories.parking_repository import DEFAULT_PARKING_FIXTURES


def seed_simulated_demonstration_data():
    """
    Explicitly labeled simulated data seed script for local demonstration only.
    NOTICE:
    - Never run automatically in production.
    - All seeded records have isSimulated=True, coordinateSource='simulated-development',
      and dataSource='simulated-development'.
    - Never stores ML predictions as actual live occupancy.
    """
    if settings.ENVIRONMENT.lower() == "production":
        print("❌ ABORTED: Cannot seed demonstration data into a production environment.")
        sys.exit(1)

    print("=================================================================")
    print("PARKSMART AI: LOCAL DEMONSTRATION SEED UTILITY")
    print("NOTICE: All records are synthetic / simulated. Not for production.")
    print("=================================================================")
    print(f"Connecting to MongoDB at: {settings.MONGODB_URI}")

    client = MongoClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS
    )
    try:
        client.admin.command("ping")
        db = client[settings.MONGODB_DB_NAME]

        # 1. Ensure indexes first
        print("Ensuring unique and query indexes...")
        ensure_parking_indexes(db)

        # 2. Upsert synthetic fixtures idempotently
        print(f"Upserting {len(DEFAULT_PARKING_FIXTURES)} simulated Pune parking demonstration fixtures...")
        for fixture in DEFAULT_PARKING_FIXTURES:
            db.parking.update_one(
                {"id": fixture["id"]},
                {"$set": dict(fixture)},
                upsert=True
            )

        print("✅ Local demonstration data seeded successfully:")
        cursor = db.parking.find(
            {},
            {"_id": 0, "id": 1, "name": 1, "totalCapacity": 1, "coordinates": 1, "isSimulated": 1}
        )
        for doc in cursor:
            print(
                f" - [{doc['id']}] {doc['name']} "
                f"(Capacity: {doc['totalCapacity']}, Coordinates: {doc['coordinates']}, Simulated: {doc['isSimulated']})"
            )

    except Exception as e:
        print(f"❌ Error connecting or seeding MongoDB: {e}")
        print("Ensure local MongoDB is running, or verify your MONGODB_URI in .env.")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    seed_simulated_demonstration_data()
