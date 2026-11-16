import logging
from pymongo.database import Database
from pymongo import ASCENDING

logger = logging.getLogger("parksmart.db.indexes")


def ensure_parking_indexes(db: Database) -> None:
    """
    Idempotent index creation for parking and authentication collections.
    Can safely be executed multiple times without recreating or failing.
    Indexes:
    - Unique stable parking IDs and account usernames.
    - Parking simulation/timestamp query fields.
    - Unique revoked-token IDs with expiry cleanup.
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
        db.users.create_index(
            [("username", ASCENDING)],
            unique=True,
            name="uq_user_username",
        )
        db.revoked_tokens.create_index(
            [("jti", ASCENDING)],
            unique=True,
            name="uq_revoked_token_jti",
        )
        db.revoked_tokens.create_index(
            [("expiresAt", ASCENDING)],
            expireAfterSeconds=0,
            name="ttl_revoked_token_expiration",
        )
        logger.info("All database indexes verified successfully.")
    except Exception as e:
        logger.error("Error creating database indexes (%s).", type(e).__name__)
        raise
