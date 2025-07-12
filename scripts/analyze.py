from dotenv import load_dotenv
import os
import sys
from analyzer.slack_api import fetch_slack_messages, SlackAPIError
from analyzer.alarm_parser import analyze_alarms, display_alarm_statistics, parse_date

def main():
    if len(sys.argv) != 3:
        print("Usage: python analyze.py <date> <mode>")
        print("Date format: dd-mm-yy (e.g., 24-06-25)")
        print("Mode: SEND or INTEROP")
        sys.exit(1)

    date_str = sys.argv[1]
    mode = sys.argv[2].upper()

    if mode not in ['SEND', 'INTEROP']:
        print("Error: mode must be either SEND or INTEROP")
        sys.exit(1)

    # Read token and channel from env variables
    load_dotenv()  # this loads variables from .env into the environment

    bot_token = os.getenv('SLACK_TOKEN')
    if not bot_token:
        print("Error: SLACK_TOKEN environment variable not set")
        sys.exit(1)

    print(bot_token)
    
    channel_env_var = 'SLACK_CHANNEL_SEND' if mode == 'SEND' else 'SLACK_CHANNEL_INTEROP'
    channel_id = os.getenv(channel_env_var)
    if not channel_id:
        print(f"Error: {channel_env_var} environment variable not set")
        sys.exit(1)

    try:
        oldest, latest, formatted_date = parse_date(date_str)
    except ValueError as e:
        print(f"Date parsing error: {e}")
        sys.exit(1)

    print(f"Analyzing alarm messages for {formatted_date} in mode: {mode}")
    print(f"Channel ID: {channel_id}")

    try:
        messages = fetch_slack_messages(channel_id, bot_token, oldest, latest)
    except SlackAPIError as e:
        print(f"Slack API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Network or HTTP error: {e}")
        sys.exit(1)

    alarm_stats, total_alarms = analyze_alarms(messages, mode)

    display_alarm_statistics(alarm_stats, total_alarms, formatted_date)


if __name__ == "__main__":
    main()