from dotenv import load_dotenv
import os
import sys
import warnings
from datetime import datetime, timezone

# Suppress urllib3 warning about OpenSSL version
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

from analyzer.slack import fetch_slack_messages, SlackAPIError
from analyzer.utils import get_time_bounds
from analyzer.alarm_parser import parse_open_closing_pairs
from analyzer.duration_params import DurationParams

def format_duration(seconds):
    if seconds is None:
        return "OPEN"
    else:
        delta = datetime(seconds)
        return str(delta)

def print_usage():
    """Print usage information."""
    print("Usage: python open_duration.py [<days_back>] [report=formats]")
    print("")
    print("Examples:")
    print("  python open_duration.py")
    print("  python open_duration.py 3")
    print("  python open_duration.py 7 report=html")
    print("  python open_duration.py 3 report=html,pdf")
    print("  python open_duration.py report=pdf,csv")
    print("  python open_duration.py 7 report=html,pdf,csv,json")
    print("  python open_duration.py report=json")
    print("Report formats: html, pdf, csv, json (default: html)")

def parse_arguments():
    """Parse command line arguments including report formats."""
    # Check for help flag
    if any(arg in ['-h', '--help'] for arg in sys.argv[1:]):
        print_usage()
        sys.exit(0)

    # Define valid formats with their corresponding methods
    valid_formats = {
        'html': {'class': 'HtmlReporter', 'module': 'analyzer.reporting.html_reporter' },
        'pdf': { 'class': 'PdfReporter', 'module': 'analyzer.reporting.pdf_reporter' },
        'csv': { 'class': 'CsvReporter', 'module': 'analyzer.reporting.csv_reporter' },
        'json': { 'class': 'JsonReporter', 'module': 'analyzer.reporting.json_reporter' },
    }

    # Parse arguments
    days_back = 1
    report_formats = ['html']  # Default

    for arg in sys.argv[1:]:
        if arg.startswith('report='):
            # Parse report formats
            formats_str = arg.split('=', 1)[1]
            report_formats = [fmt.strip() for fmt in formats_str.split(',')]

            # Validate report formats
            invalid_formats = [fmt for fmt in report_formats if fmt not in valid_formats]
            if invalid_formats:
                print(f"Error: Invalid report format(s): {', '.join(invalid_formats)}")
                print(f"Valid formats are: {', '.join(sorted(valid_formats.keys()))}")
                sys.exit(1)
        else:
            try:
                days_back = int(arg)
            except ValueError:
                print(f"Error: Invalid argument '{arg}'. Expected integer or report=formats")
                sys.exit(1)

    return days_back, report_formats, valid_formats

def main():
    days_back, report_formats, valid_formats = parse_arguments()

    load_dotenv()

    bot_token = os.getenv('SLACK_TOKEN')
    channel_id = os.getenv('SLACK_CHANNEL_SEND')

    if not bot_token or not channel_id:
        print("Error: SLACK_TOKEN or SLACK_CHANNEL_SEND not set")
        sys.exit(1)

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

    # Generate reports based on requested formats
    date_str = datetime.fromtimestamp(latest).strftime("%Y-%m-%d")

    # Create DurationParams object
    duration_params = DurationParams(
        durations=durations,
        date_str=date_str,
        days_back=days_back,
        oldest=oldest,
        latest=latest,
        num_messages=len(messages),
        num_openings=len(openings),
        num_closings=len(closings)
    )

    print("")  # Add blank line before report output

    # Generate reports for each requested format
    for format_name in report_formats:
        try:
            format_config = valid_formats[format_name]
            module_name = format_config['module']
            class_name = format_config['class']

            # Import the module dynamically
            module = __import__(module_name, fromlist=[class_name])
            reporter_class = getattr(module, class_name)

            # Instantiate reporter
            reporter = reporter_class()

            # Generate report with DurationParams object
            report_path = reporter.generate_open_duration_report(duration_params)

            print(f"{format_name.upper()} report generated at: {report_path}")

        except ImportError as e:
            # Handle specific import errors with helpful messages
            error_msg = str(e).lower()
            if 'weasyprint' in error_msg:
                print(f"{format_name.upper()} report generation failed: WeasyPrint not available. Install with: pip install weasyprint")
            else:
                print(f"{format_name.upper()} report generation failed: {e}")

        except Exception as e:
            print(f"{format_name.upper()} report generation failed: {e}")

if __name__ == "__main__":
    main()