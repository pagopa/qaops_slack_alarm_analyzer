import re
from datetime import datetime
from collections import defaultdict, Counter
from .config import IgnoreRuleParser
from .analyzer_params import AnalyzerParams
from .slack import SlackMessageParserProvider

DETAILED_TIME_HISTOGRAM = True  # Set False to disable hourly distribution
OPENING_PATTERN = re.compile(r'#(\d+): ALARM: "([^"]+)" in (.+)')
CLOSING_PATTERN = re.compile(r'CloudWatch closed alert .*?\|#(\d+)> "ALARM:\s*"([^"]+)"\s*in\s+([^"]+)"')

def parse_slack_ts(ts_str):
    return datetime.fromtimestamp(float(ts_str))

def extract_alarm_info(message):
    """Extract alarm info for SEND mode from Slack message attachments."""
    if not message.get('attachments') or len(message['attachments']) == 0:
        return None

    attachment = message['attachments'][0]
    title = attachment.get('title', '')
    fallback = attachment.get('fallback', '')

    # Nuovo pattern per TITLE: "#45533: ALARM: \"AlarmName\" in Location"
    title_pattern = OPENING_PATTERN
    title_match = re.search(title_pattern, title)

    if title_match:
        alarm_id = title_match.group(1)
        alarm_name = title_match.group(2)
        location = title_match.group(3)

        ts = message.get("ts")
        timestamp = parse_slack_ts(ts) if ts else None

        return {
            'id': alarm_id,
            'name': alarm_name,
            "timestamp": timestamp,
            'location': location,
            'full_text': title
        }
    
    return None

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

def analyze_alarms(messages, params: AnalyzerParams):
    """
    Analyze alarm messages and aggregate by alarm name.

    Returns:
        tuple: (alarm_stats, analyzed_alarms, total_alarms, ignored_messages)
            - alarm_stats: dict of alarm name -> list of alarm info
            - analyzed_alarms: count of alarms analyzed (total - ignored)
            - total_alarms: total count of ALARM messages found (includes ignored)
            - ignored_messages: list of ignored alarm info
    """
    alarm_stats = defaultdict(list)
    total_alarms = 0  # Total count of ALARM messages (both analyzed and ignored)
    ignored_messages = []

    # Get ignore rules from the product configuration passed in params
    applicable_rules = params.product_rules
    ignore_rule_parser = IgnoreRuleParser(applicable_rules)

    # Get the appropriate parser for this product-environment combination
    parser_provider = SlackMessageParserProvider()
    slack_parser = parser_provider.get_parser(params.product, params.environment)

    if not slack_parser:
        raise ValueError(f"No parser available for product '{params.product}' environment '{params.environment}'")

    for message in messages:
        # First, try to parse the message as an alarm
        alarm_info = slack_parser.extract_alarm_info(message)

        # Only process if it's an alarm message
        if alarm_info:
            total_alarms += 1  # Count all alarms (both ignored and analyzed)

            # Check if this alarm should be ignored
            if ignore_rule_parser.should_ignore_message(message, params.environment):
                ignored_info = create_ignored_message_info(message, ignore_rule_parser)
                ignored_messages.append(ignored_info)
            else:
                # This alarm should be analyzed
                alarm_stats[alarm_info['name']].append(alarm_info)

    # Calculate analyzed alarms = total alarms - ignored alarms
    analyzed_alarms = total_alarms - len(ignored_messages)

    print(f"Ignored {len(ignored_messages)} alarm messages based on ignore patterns")
    return alarm_stats, analyzed_alarms, total_alarms, ignored_messages

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

def parse_open_closing_pairs(messages):
    openings = {}
    closings = {}

    for msg in messages:
        if 'attachments' not in msg:
            continue

        attachment = msg['attachments'][0]
        fallback = attachment.get('fallback', '')
        title = attachment.get('title', '')
        ts = float(msg.get('ts', 0))

        # Aperture: dal campo "title"
        open_match = re.search(OPENING_PATTERN, title)
        if open_match:
            alarm_id, alarm_name, region = open_match.groups()
            openings[alarm_id] = (ts, alarm_name)
            continue

        # Chiusure: dal campo "fallback"
        close_match = re.search(CLOSING_PATTERN, fallback)
        if close_match:
            alarm_id = close_match.group(1)
            closings[alarm_id] = ts
            continue

    return openings, closings

def create_ignored_message_info(message, ignore_rule_parser):
    """Create ignored message info dictionary from a Slack message."""
    ignored_info = {
        'timestamp': parse_slack_ts(message.get('ts', '0')),
        'text': message.get('text', ''),
        'reason': ignore_rule_parser.get_ignore_reason(message)
    }

    # Extract additional info from attachments
    if message.get('attachments'):
        attachment = message['attachments'][0]
        ignored_info['title'] = attachment.get('title', '')
        ignored_info['fallback'] = attachment.get('fallback', '')

    # Extract info from files
    if message.get('files'):
        file_info = message['files'][0]
        ignored_info['file_name'] = file_info.get('name', '')
        ignored_info['file_text'] = file_info.get('plain_text', '')[:400] + '...' if len(file_info.get('plain_text', '')) > 400 else file_info.get('plain_text', '')

    return ignored_info