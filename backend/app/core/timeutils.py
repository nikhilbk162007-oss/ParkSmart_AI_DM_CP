from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def normalize_target_time(value: datetime) -> datetime:
    """Interpret naive request times in the configured application timezone."""
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=ZoneInfo(settings.APP_TIMEZONE))
    return value
