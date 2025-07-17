from datetime import datetime, timedelta

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