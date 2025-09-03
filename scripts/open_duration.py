from dotenv import load_dotenv
import os
import sys
from datetime import datetime
from analyzer.slack_api import fetch_slack_messages, SlackAPIError
from analyzer.time_utils import get_time_bounds
from analyzer.alarm_parser import parse_open_closing_pairs
from datetime import datetime, timezone
from analyzer.report import generate_duration_report

def format_duration(seconds):
    if seconds is None:
        return "OPEN"
    else:
        delta = datetime(seconds)
        return str(delta)

def main():
    load_dotenv()

    bot_token = os.getenv('SLACK_TOKEN')
    channel_id = os.getenv('SLACK_CHANNEL_SEND')

    if not bot_token or not channel_id:
        print("Error: SLACK_TOKEN or SLACK_CHANNEL_SEND not set")
        sys.exit(1)

    if len(sys.argv) > 2:
        print("Usage: python open_duration.py [<days_back>]")
        sys.exit(1)

    days_back = int(sys.argv[1]) if len(sys.argv) == 2 else 1
    if days_back > 30:
        print("Error: days_back cannot be greater than 30.")
        sys.exit(1)

    oldest, latest = get_time_bounds(days_back)

    print(f"Fetching messages from the last {days_back} day(s)...")
    print(f"from: ", datetime.fromtimestamp(oldest).strftime('%Y-%m-%d %H:%M:%S'))
    print(f"to: ", datetime.fromtimestamp(latest).strftime('%Y-%m-%d %H:%M:%S'))

    try:
        messages = fetch_slack_messages(channel_id, bot_token, oldest, latest)
        print(f"Fetched {len(messages)} messages")
    except SlackAPIError as e:
        print(f"Slack API error: {e}")
        sys.exit(1)

    openings, closings = parse_open_closing_pairs(messages)
    print(f"openings {len(openings)} openings")
    print(f"closings {len(closings)} closings")

    # Match openings and closings
    durations = []
    for alarm_id, (open_ts, alarm_name) in openings.items():
        close_ts = closings.get(alarm_id)
        now = datetime.now(timezone.utc).timestamp()
        duration = (close_ts - open_ts) if close_ts else (now - open_ts)  # in hours
        durations.append((alarm_id, alarm_name, open_ts, close_ts, duration))

    # Add still open alarms
    now = datetime.now(timezone.utc).timestamp()
    durations.sort(
        key=lambda x: x[4] if x[4] is not None else now - x[2],  # x[2] è open_ts
        reverse=True
    )

    print("\n--- Alarm Durations (longest open first) ---")
    for alarm_id, alarm_name, open_ts, close_ts, duration in durations:
        open_time = datetime.fromtimestamp(open_ts).strftime('%Y-%m-%d %H:%M:%S')
        name_field = alarm_name.ljust(60)  # adatta larghezza se vuoi
        if close_ts:
            close_time = datetime.fromtimestamp(close_ts).strftime('%Y-%m-%d %H:%M:%S')
            if duration >= 3600:
                dur_str = f"{duration / 3600:.0f} hours"
            else:
                dur_str = f"{duration / 60:.0f} minutes"
            print(f"#{name_field} | {alarm_id}  | Opened: {open_time} | Closed: {close_time} | Duration: {dur_str}")
        else:
            print(f"#{name_field} | {alarm_id}  | Opened: {open_time} | STILL OPEN")

    # Crea HTML report
    date_str = datetime.fromtimestamp(latest).strftime("%Y-%m-%d")
    report_path = generate_duration_report(
        durations=durations,
        date_str=date_str,
        days_back=days_back,
        oldest=oldest,
        latest=latest,
        num_messages=len(messages),
        num_openings=len(openings),
        num_closings=len(closings)
    )
    print(f"\n📄 Report generated at: {report_path}")

if __name__ == "__main__":
    main()