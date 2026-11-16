import sys
from pymongo import MongoClient
from app.core.config import settings
from app.db.indexes import ensure_parking_indexes
from app.repositories.parking_repository import (
    DEFAULT_PARKING_FIXTURES,
    LEGACY_SIMULATED_FIXTURE_IDS,
)


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
    print("Connecting to the configured MongoDB server.")

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

        # Remove only the previous known simulated demo records.
        db.parking.delete_many({
            "id": {"$in": list(LEGACY_SIMULATED_FIXTURE_IDS)},
            "isSimulated": True,
        })

        # Upsert the fixed fictional campus simulation facilities.
        print(f"Upserting {len(DEFAULT_PARKING_FIXTURES)} simulated campus facilities...")
        for fixture in DEFAULT_PARKING_FIXTURES:
            db.parking.update_one(
                {"id": fixture["id"]},
                {"$set": dict(fixture)},
                upsert=True
            )

        print("SUCCESS: Local demonstration data seeded successfully:")
        cursor = db.parking.find(
            {},
            {
                "_id": 0,
                "id": 1,
                "name": 1,
                "totalCapacity": 1,
                "currentOccupancy": 1,
                "acceptedVehicleTypes": 1,
                "isSimulated": 1,
            }
        )
        for doc in cursor:
            print(
                f" - [{doc['id']}] {doc['name']} "
                f"(Capacity: {doc['totalCapacity']}, "
                f"Occupied: {doc.get('currentOccupancy', {}).get('occupiedSpaces')}, "
                f"Simulated: {doc['isSimulated']})"
            )

    except Exception as e:
        print(f"ERROR: Connecting or seeding MongoDB failed ({type(e).__name__}).")
        print("Ensure local MongoDB is running, or verify your MONGODB_URI in .env.")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    seed_simulated_demonstration_data()
