"""
Sleep utilities for farming
"""

import pytz
from datetime import datetime, timedelta


def get_sleep_until(minutes: int = None, seconds: int = None, hours: int = None, days: int = None) -> datetime:
    """Get future datetime after sleeping for specified duration"""
    duration = timedelta()
    
    if days is not None:
        duration += timedelta(days=days)
    
    if hours is not None:
        duration += timedelta(hours=hours)
    
    if minutes is not None:
        duration += timedelta(minutes=minutes)
    
    if seconds is not None:
        duration += timedelta(seconds=seconds)
    
    return datetime.now(pytz.UTC) + duration


async def verify_sleep(value: datetime) -> bool:
    """Verify if sleep time has passed"""
    if value is None:
        return True
    
    current_time = datetime.now(pytz.UTC)
    
    # Handle both timezone-aware and naive datetimes
    if value.tzinfo is None:
        sleep_until = value.replace(tzinfo=pytz.UTC)
    else:
        sleep_until = value.astimezone(pytz.UTC)
    
    if sleep_until > current_time:
        return False
    return True
