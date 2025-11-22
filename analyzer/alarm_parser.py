import re
from datetime import datetime
from collections import defaultdict, Counter
from .config import IgnoreRuleParser, is_oncall_in_reperibilita
from .analyzer_params import AnalyzerParams
from .slack import SlackMessageParserProvider
from .alarm_type import AlarmType
from .alarm_analysis_result import AlarmAnalysisResult

DETAILED_TIME_HISTOGRAM = True  # Set False to disable hourly distribution
OPENING_PATTERN = re.compile(r'#(\d+): ALARM: "([^"]+)" in (.+)')
CLOSING_PATTERN = re.compile(r'CloudWatch closed alert .*?\|#(\d+)> "ALARM:\s*"([^"]+)"\s*in\s+([^"]+)"')

def parse_slack_ts(ts_str):
    return datetime.fromtimestamp(float(ts_str))

def analyze_alarms(messages, alarm_type: AlarmType, product_config):
    """
    Analyze alarm messages and filter by alarm type.

    Args:
        messages: List of raw Slack messages
        alarm_type: AlarmType instance defining the type of alarms to analyze
        product_config: Product configuration for ignore rules

    Returns:
        AlarmAnalysisResult: Analysis results for this alarm type
    """
    alarm_stats = defaultdict(list)
    total_alarms = 0
    ignored_messages = []
    oncall_total = 0
    oncall_in_reperibilita = 0

    # Get ignore rules from the product configuration
    applicable_rules = product_config.ignore_rules if product_config else []
    ignore_rule_parser = IgnoreRuleParser(applicable_rules)

    # Get the appropriate parser for this alarm type's product-environment
    oncall_config = product_config.oncall_config if product_config else None
    parser_provider = SlackMessageParserProvider()
    slack_parser = parser_provider.get_parser(alarm_type.product, alarm_type.environment, oncall_config)

    if not slack_parser:
        raise ValueError(f"No parser available for product '{alarm_type.product}' environment '{alarm_type.environment}'")

    for message in messages:
        # First, try to parse the message as an alarm
        alarm_info = slack_parser.extract_alarm_info(message)

        # Only process if it's an alarm message
        if alarm_info:
            alarm_name = alarm_info.get('name', '')

            # Filter by alarm type pattern
            if not alarm_type.matches_alarm_name(alarm_name):
                continue

            total_alarms += 1

            # Track oncall statistics (only for oncall alarm types)
            if alarm_type.is_oncall():
                oncall_total += 1
                alarm_timestamp = alarm_info.get('timestamp')
                if alarm_timestamp and is_oncall_in_reperibilita(alarm_timestamp):
                    oncall_in_reperibilita += 1

            # Check if this alarm should be ignored
            alarm_timestamp = alarm_info.get('timestamp')
            if ignore_rule_parser.should_ignore_message(message, alarm_type.environment, alarm_timestamp):
                ignored_info = create_ignored_message_info(message, ignore_rule_parser, alarm_info, alarm_type.environment)
                ignored_messages.append(ignored_info)
            else:
                # This alarm is analyzable
                alarm_stats[alarm_name].append(alarm_info)

    # Calculate analyzable alarms
    analyzable_alarms = total_alarms - len(ignored_messages)

    print(f"[{alarm_type}] Total: {total_alarms}, Analyzable: {analyzable_alarms}, Ignored: {len(ignored_messages)}")
    if alarm_type.is_oncall():
        print(f"[{alarm_type}] OnCall: {oncall_total} total, {oncall_in_reperibilita} in reperibilità")

    # Return AlarmAnalysisResult
    return AlarmAnalysisResult(
        alarm_stats=dict(alarm_stats),
        total_alarms=total_alarms,
        analyzable_alarms=analyzable_alarms,
        ignored_alarms=len(ignored_messages),
        ignored_messages=ignored_messages,
        oncall_total=oncall_total,
        oncall_in_reperibilita=oncall_in_reperibilita,
        alarm_type=alarm_type
    )

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

def create_ignored_message_info(message, ignore_rule_parser, alarm_info, environment=None):
    """Create ignored message info dictionary from a Slack message.

    Args:
        message: The Slack message
        ignore_rule_parser: Parser for ignore rules
        alarm_info: Parsed alarm information (contains alarm name, id, etc.)
        environment: Environment name for rule matching
    """
    # Use the alarm's timestamp for validity checking (not current time)
    alarm_timestamp = alarm_info['timestamp'] if alarm_info else parse_slack_ts(message.get('ts', '0'))

    # Get the matched rule to extract validity and exclusions
    matched_rule = ignore_rule_parser.get_matched_rule(message, environment, alarm_timestamp)

    ignored_info = {
        'name': alarm_info['name'] if alarm_info else 'Unknown',
        'id': alarm_info['id'] if alarm_info else 'N/A',
        'timestamp': alarm_timestamp,
        'reason': ignore_rule_parser.get_ignore_reason(message, environment, alarm_timestamp),
        'text': message.get('text', ''),
        'validity': matched_rule.validity if matched_rule and matched_rule.validity and not matched_rule.validity.is_empty() else None,
        'exclusions': matched_rule.exclusions if matched_rule and matched_rule.exclusions and not matched_rule.exclusions.is_empty() else None
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