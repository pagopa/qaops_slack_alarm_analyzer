from datetime import datetime, timedelta
import pytz

ROME_TZ = pytz.timezone('Europe/Rome')

def get_evening_window(date_str: str) -> tuple[float, float]:
    # Parse the given date string (format: DD-MM-YY)
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
