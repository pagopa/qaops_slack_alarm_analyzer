from dotenv import load_dotenv
from datetime import datetime
import os
import sys
import warnings

# Suppress urllib3 warning about OpenSSL version
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

from analyzer.slack import fetch_slack_messages, SlackAPIError
from analyzer.alarm_parser import analyze_alarms
from analyzer.utils import get_evening_window
from analyzer.config.config_reader import ConfigReader
from analyzer.analyzer_params import AnalyzerParams
from analyzer.alarm_type import build_alarm_types
from analyzer.alarm_analysis_result import merge_analysis_results

def parse_arguments():
    """Parse command line arguments including report formats."""
    if len(sys.argv) < 3:
        print("Usage: python analyze.py <date|date_range> <product> [environment] [report=formats]")
        print("Date formats:")
        print("  Single date: DD-MM-YY (e.g., 19-09-25)")
        print("  Date range: DD-MM-YY:DD-MM-YY (e.g., 19-09-25:21-09-25)")
        print("")
        print("Examples:")
        print("  python analyze.py 19-09-25 SEND")
        print("  python analyze.py 19-09-25:21-09-25 SEND")
        print("  python analyze.py 19-09-25 SEND prod")
        print("  python analyze.py 19-09-25:21-09-25 INTEROP test")
        print("  python analyze.py 19-09-25 SEND prod report=html")
        print("  python analyze.py 19-09-25:21-09-25 SEND prod report=html,json")
        print("  python analyze.py 19-09-25 SEND prod report=pdf,csv")
        print("Report formats: html, pdf, csv, json (default: html)")
        sys.exit(1)

    date_str = sys.argv[1]
    product = sys.argv[2].upper()

    # Define valid formats with their corresponding reporter classes
    valid_formats = {
        'html': {'class': 'HtmlReporter', 'module': 'analyzer.reporting.html_reporter' },
        'pdf': { 'class': 'PdfReporter', 'module': 'analyzer.reporting.pdf_reporter' },
        'csv': { 'class': 'CsvReporter', 'module': 'analyzer.reporting.csv_reporter' },
        'json': { 'class': 'JsonReporter', 'module': 'analyzer.reporting.json_reporter' }
    }

    # Parse remaining arguments for environment and report
    environment = 'prod'
    report_formats = ['html']  # Default

    for i in range(3, len(sys.argv)):
        arg = sys.argv[i]
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
            # Assume it's environment if not a report parameter
            environment = arg

    return date_str, product, environment, report_formats, valid_formats

def main():
    date_str, product, environment, report_formats, valid_formats = parse_arguments()

    # Load and validate configuration
    try:
        config_reader = ConfigReader()
        config_reader.load_config()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Validate product
    available_products = config_reader.get_product_names()
    if product not in available_products:
        print(f"Error: product must be one of: {', '.join(available_products)}")
        sys.exit(1)

    # Validate environment for the specific product
    available_environments = config_reader.get_environment_names(product)
    if environment not in available_environments:
        print(f"Error: environment must be one of: {', '.join(available_environments)} for product {product}")
        sys.exit(1)

    # Get product configuration
    product_config = config_reader.get_product_config(product)
    if not product_config:
        print(f"Error: Could not load configuration for product {product}")
        sys.exit(1)

    # Get Slack channel ID from configuration
    slack_channel_id = product_config.get_slack_channel_id(environment)
    if not slack_channel_id:
        print(f"Error: No Slack channel ID configured for product {product} environment {environment}")
        sys.exit(1)

    # Read Slack token from env variables
    load_dotenv()  # this loads variables from .env into the environment

    bot_token = os.getenv('SLACK_TOKEN')
    if not bot_token:
        print("Error: SLACK_TOKEN environment variable not set")
        sys.exit(1)

    # Build alarm types for this product/environment
    alarm_types = build_alarm_types(product_config, product, environment)

    if not alarm_types:
        print(f"Error: No alarm types configured for product {product} environment {environment}")
        sys.exit(1)

    print(f"\n=== Alarm Analysis ===")
    print(f"Product: {product}")
    print(f"Environment: {environment}")
    print(f"Date: {date_str}")
    print(f"Alarm types to analyze: {len(alarm_types)}")
    for at in alarm_types:
        print(f"  - {at}")

    # Analyze each alarm type separately
    analysis_results = []

    for alarm_type in alarm_types:
        print(f"\n=== Processing {alarm_type} ===")

        # Get time window for this alarm type
        try:
            oldest, latest = alarm_type.get_time_window(date_str)
        except ValueError as e:
            print(f"Date parsing error: {e}")
            continue

        print(f"Time window: {datetime.fromtimestamp(oldest).strftime('%Y-%m-%d %H:%M:%S')} to {datetime.fromtimestamp(latest).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Channel ID: {alarm_type.channel_id}")

        # Fetch messages for this alarm type's channel and time window
        try:
            messages = fetch_slack_messages(alarm_type.channel_id, bot_token, oldest, latest)
            print(f"Fetched {len(messages)} messages from channel")
        except SlackAPIError as e:
            print(f"Slack API error: {e}")
            continue
        except Exception as e:
            print(f"Network or HTTP error: {e}")
            continue

        # Analyze alarms for this type
        try:
            result = analyze_alarms(messages, alarm_type, product_config)
            analysis_results.append(result)
        except Exception as e:
            print(f"Analysis error: {e}")
            continue

    # Merge all results
    if not analysis_results:
        print("\nNo analysis results to process")
        sys.exit(1)

    merged_result = merge_analysis_results(analysis_results)

    # Extract values from merged result for backward compatibility
    alarm_stats = merged_result.alarm_stats
    analyzable_alarms = merged_result.analyzable_alarms
    total_alarms = merged_result.total_alarms
    ignored_messages = merged_result.ignored_messages
    oncall_total = merged_result.oncall_total
    oncall_in_reperibilita = merged_result.oncall_in_reperibilita

    # Create analyzer parameters for reporters (using main channel and evening window for backward compatibility)
    try:
        oldest, latest = get_evening_window(date_str)
        analyzer_params = AnalyzerParams(
            date_str=date_str,
            product=product,
            environment=environment,
            slack_channel_id=slack_channel_id,
            oldest=oldest,
            latest=latest,
            product_config=product_config,
            slack_token=bot_token
        )
    except ValueError as e:
        print(f"Parameter creation error: {e}")
        sys.exit(1)

    # Print statistics
    print(f"\n=== Alarm Statistics ===")
    print(f"Total alarms found:      {total_alarms}")
    print(f"Alarms ignored:          {len(ignored_messages)}")
    print(f"Alarms analyzable:       {analyzable_alarms}")
    if oncall_total > 0:
        print(f"\n=== OnCall Statistics ===")
        print(f"Total oncall alarms:     {oncall_total}")
        print(f"OnCall in reperibilità:  {oncall_in_reperibilita}")

    # Generate reports based on requested formats
    for format_name in report_formats:
        try:
            format_config = valid_formats[format_name]
            module_name = format_config['module']
            class_name = format_config['class']

            # Import the module dynamically
            module = __import__(module_name, fromlist=[class_name])
            reporter_class = getattr(module, class_name)

            # Instantiate and generate report
            reporter = reporter_class()
            report_path = reporter.generate_report(
                alarm_stats, analyzable_alarms, total_alarms, analyzer_params, ignored_messages,
                oncall_total, oncall_in_reperibilita
            )
            print(f"{format_name.upper()} report generated at: {report_path}")

        except ImportError as e:
            # Handle specific import errors with helpful messages
            error_msg = str(e).lower()
            if 'weasyprint' in error_msg:
                print(f"{format_name.upper()} report generation failed: WeasyPrint not available. Install with: pip install weasyprint")
            elif 'jinja2' in error_msg:
                print(f"{format_name.upper()} report generation failed: Jinja2 not available. Install with: pip install Jinja2")
            else:
                print(f"{format_name.upper()} report generation failed: {e}")

        except Exception as e:
            print(f"{format_name.upper()} report generation failed: {e}")

if __name__ == "__main__":
    main()