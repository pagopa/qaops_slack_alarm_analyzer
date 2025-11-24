from datetime import datetime, timedelta
import pytz

ROME_TZ = pytz.timezone('Europe/Rome')

def get_evening_window(date_str: str) -> tuple[float, float]:
    """
    Parse date string and return time window.

    Args:
        date_str: Single date (DD-MM-YY) or date range (DD-MM-YY:DD-MM-YY)

    Returns:
        tuple[float, float]: (start_timestamp, end_timestamp)
    """
    # Check if it's a date range (contains colon separator)
    if ':' in date_str:
        start_date_str, end_date_str = date_str.split(':', 1)

        # Parse both dates (format: DD-MM-YY)
        start_day = datetime.strptime(start_date_str.strip(), "%d-%m-%y")
        end_day = datetime.strptime(end_date_str.strip(), "%d-%m-%y")

        # Validate date order
        if start_day > end_day:
            raise ValueError(f"Start date {start_date_str} must be before or equal to end date {end_date_str}")

        # Start from 18:00 of the day before start_day
        start_dt = ROME_TZ.localize(start_day - timedelta(days=1))
        start_dt = start_dt.replace(hour=18, minute=0, second=0, microsecond=0)

        # End at 18:00 of end_day
        end_dt = ROME_TZ.localize(end_day)
        end_dt = end_dt.replace(hour=18, minute=0, second=0, microsecond=0)

    else:
        # Single date - backward compatibility
        target_day = datetime.strptime(date_str, "%d-%m-%y")

        # Localize 18:00 of the previous day
        start_dt = ROME_TZ.localize(target_day - timedelta(days=1))
        start_dt = start_dt.replace(hour=18, minute=0, second=0, microsecond=0)

        # Localize 18:00 of the target day
        end_dt = ROME_TZ.localize(target_day)
        end_dt = end_dt.replace(hour=18, minute=0, second=0, microsecond=0)

    # Convert to UTC timestamps
    start_utc = start_dt.astimezone(pytz.utc).timestamp()
    end_utc = end_dt.astimezone(pytz.utc).timestamp()

    return start_utc, end_utc

def get_oncall_window(date_str: str) -> tuple[float, float]:
    """
    Parse date string and return oncall time window (00:00-23:59:59 of the date).

    OnCall alarms are counted in the actual day they occur, not in the 18:00-18:00 window.

    Args:
        date_str: Single date (DD-MM-YY) or date range (DD-MM-YY:DD-MM-YY)

    Returns:
        tuple[float, float]: (start_timestamp, end_timestamp) in UTC
    """
    # Check if it's a date range (contains colon separator)
    if ':' in date_str:
        start_date_str, end_date_str = date_str.split(':', 1)

        # Parse both dates (format: DD-MM-YY)
        start_day = datetime.strptime(start_date_str.strip(), "%d-%m-%y")
        end_day = datetime.strptime(end_date_str.strip(), "%d-%m-%y")

        # Validate date order
        if start_day > end_day:
            raise ValueError(f"Start date {start_date_str} must be before or equal to end date {end_date_str}")

        # Start from 00:00 of start_day
        start_dt = ROME_TZ.localize(start_day)
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)

        # End at 23:59:59 of end_day
        end_dt = ROME_TZ.localize(end_day)
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    else:
        # Single date
        target_day = datetime.strptime(date_str, "%d-%m-%y")

        # Localize 00:00 of the target day
        start_dt = ROME_TZ.localize(target_day)
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)

        # Localize 23:59:59 of the target day
        end_dt = ROME_TZ.localize(target_day)
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC timestamps
    start_utc = start_dt.astimezone(pytz.utc).timestamp()
    end_utc = end_dt.astimezone(pytz.utc).timestamp()

    return start_utc, end_utc


def get_time_bounds(days_back=1):
    """
    Restituisce due timestamp (Unix epoch in secondi):
    il più vecchio (oldest) e il più recente (latest) relativi agli ultimi X giorni.

    Args:
        days_back (int): Numero di giorni da cui partire a ritroso (default: 1)

    Returns:
        Tuple[int, int]: (oldest_timestamp, latest_timestamp)
    """
    now = datetime.now()
    oldest_time = now - timedelta(days=days_back)

    oldest = int(oldest_time.timestamp())
    latest = int(now.timestamp())

    return oldest, latest
