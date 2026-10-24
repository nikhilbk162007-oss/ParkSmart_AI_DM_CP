import logging
from pymongo.database import Database
from pymongo import ASCENDING

logger = logging.getLogger("parksmart.db.indexes")


def ensure_parking_indexes(db: Database) -> None:
    """
    Idempotent index creation for parking collection.
    Can safely be executed multiple times without recreating or failing.
    Indexes:
    1. 'id' - Unique index enforcing stable string parking IDs.
    2. 'is_simulated' - Compound or single index for filtering demo vs real facilities.
    3. 'created_at' - Index for timestamp ordering.
    """
    if db is None:
        logger.warning("Database reference is None. Skipping index initialization.")
        return

    try:
        # 1. Unique index on stable parking ID
        db.parking.create_index(
            [("id", ASCENDING)],
            unique=True,
            name="uq_parking_id"
        )
        logger.info("Ensured unique index 'uq_parking_id' on collection 'parking'.")

        # 2. Filter index on simulation flag
        db.parking.create_index(
            [("isSimulated", ASCENDING)],
            name="idx_parking_is_simulated"
        )

        # 3. Timestamp index
        db.parking.create_index(
            [("createdAt", ASCENDING)],
            name="idx_parking_created_at"
        )
        logger.info("All parking collection indexes verified successfully.")
    except Exception as e:
        logger.error("Error creating indexes on parking collection: %s", e)
        raise
