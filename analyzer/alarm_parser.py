import re
from datetime import datetime
from collections import defaultdict, Counter

DETAILED_TIME_HISTOGRAM = True  # Set False to disable hourly distribution

def parse_slack_ts(ts_str):
    return datetime.fromtimestamp(float(ts_str))

def extract_alarm_info(message):
    """Extract alarm info for SEND mode from Slack message attachments."""
    if not message.get('attachments') or len(message['attachments']) == 0:
        return None
    
    fallback = message['attachments'][0].get('fallback', '')
    
    # Pattern matches fallback text to extract alarm name and location
    pattern = r'^"ALARM:\s*"([^"]+)"\s*in\s+([^"]+)"'
    match = re.search(pattern, fallback)
    if match:
        alarm_name = match.group(1)
        location = match.group(2)
        
        # Extract ID from URL if present
        id_pattern = r'\|(\d+)>'
        id_match = re.search(id_pattern, fallback)
        alarm_id = id_match.group(1) if id_match else "N/A"

        ts = message.get("ts")
        timestamp = parse_slack_ts(ts) if ts else None
        
        return {
            'id': alarm_id,
            'name': alarm_name,
            "timestamp": timestamp,
            'location': location,
            'full_text': fallback
        }

def extract_alarm_info_interop(message):
    """Extract alarm info for INTEROP mode from Slack message files."""
    files = message.get('files', [])
    if not files:
        return None
    
    alarm_file = files[0]
    alarm_name = alarm_file.get('name', '')
    alarm_id = alarm_file.get('id', 'N/A')
    full_text = alarm_file.get('plain_text', '')
    
    location_match = re.search(r'in\s+(.+)', alarm_name)
    location = location_match.group(1).strip() if location_match else 'Unknown'
    
    ts = message.get('ts')
    timestamp = parse_slack_ts(ts) if ts else None
    
    return {
        'id': alarm_id,
        'name': alarm_name,
        'location': location,
        'timestamp': timestamp,
        'full_text': full_text
    }

def analyze_alarms(messages, mode):
    """Analyze alarm messages and aggregate by alarm name."""
    alarm_stats = defaultdict(list)
    total_alarms = 0
    
    extractor = extract_alarm_info if mode == 'SEND' else extract_alarm_info_interop
    
    for message in messages:
        alarm_info = extractor(message)
        if alarm_info:
            total_alarms += 1
            alarm_stats[alarm_info['name']].append(alarm_info)
    
    return alarm_stats, total_alarms

def print_hourly_distribution(timestamps):
    """Print a 24-hour distribution of timestamps."""
    hours = [ts.hour for ts in timestamps if ts]
    hour_counts = Counter(hours)
    
    for hour in range(24):
        count = hour_counts.get(hour, 0)
        if count == 0:
            continue
        
        if count <= 2:
            icon = "🔹"
        elif count <= 5:
            icon = "🔸"
        elif count <= 9:
            icon = "🔺"
        else:
            icon = "🔥"
        
        print(f"{icon} {hour:02d}:00–{(hour + 1) % 24:02d}:00 → {count} occurrences")

def display_alarm_statistics(alarm_stats, total_alarms):
    """Display summary statistics of alarms."""
    if total_alarms == 0:
        print(f"No alarm messages found for this range")
        return
    
    print("=" * 50)
    
    sorted_alarms = sorted(alarm_stats.items(), key=lambda x: len(x[1]), reverse=True)
    
    for alarm_name, alarm_entries in sorted_alarms:
        count = len(alarm_entries)
        ids_str = ', '.join(
            [f"#{alarm['id']} ({alarm['timestamp'].strftime('%d-%m-%Y %H:%M:%S')})" for alarm in alarm_entries[:10]]
        )
        if count > 10:
            ids_str += f" ... and {count - 10} more"
        
        print(f"\n{count} x {alarm_name}")
        print(f"   IDs: {ids_str}")
        
        if DETAILED_TIME_HISTOGRAM and alarm_entries:
            timestamps = [alarm['timestamp'] for alarm in alarm_entries]
            print_hourly_distribution(timestamps)
    
    print("\n" + "=" * 50)


def parse_date(date_str):
    """
    Convert a date string in 'dd-mm-yy' format to Unix timestamps (start and end of day),
    and return a nicely formatted date string.
    """
    try:
        date_obj = datetime.strptime(date_str, "%d-%m-%y")
        start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        oldest = int(start_of_day.timestamp())
        latest = int(end_of_day.timestamp())
        
        formatted_date = date_obj.strftime("%d-%m-%Y")
        return oldest, latest, formatted_date
    except ValueError:
        print("Error: Invalid date format. Please use dd-mm-yy (e.g., 24-06-25)")
        import sys; sys.exit(1)