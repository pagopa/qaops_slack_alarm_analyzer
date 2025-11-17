"""
KPI Report Generator for QAOps Slack Alarm Analyzer.

Generates comprehensive KPI reports across all products and environments
for a specified date range.
"""
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import sys
import warnings
from typing import Dict, Any, List

# Suppress urllib3 warning about OpenSSL version
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

from analyzer.slack import fetch_slack_messages, SlackAPIError
from analyzer.alarm_parser import analyze_alarms
from analyzer.utils import get_evening_window
from analyzer.config.config_reader import ConfigReader
from analyzer.analyzer_params import AnalyzerParams


def parse_date_range(date_range_str: str) -> List[str]:
    """
    Parse date range string and return list of dates.

    Args:
        date_range_str: Date range in format DD-MM-YY:DD-MM-YY or single date DD-MM-YY

    Returns:
        List of date strings in DD-MM-YY format
    """
    if ':' in date_range_str:
        # Date range
        start_str, end_str = date_range_str.split(':')
        start_date = datetime.strptime(start_str, '%d-%m-%y')
        end_date = datetime.strptime(end_str, '%d-%m-%y')

        if start_date > end_date:
            raise ValueError("Start date must be before or equal to end date")

        # Generate list of dates
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date.strftime('%d-%m-%y'))
            current_date += timedelta(days=1)

        return dates
    else:
        # Single date
        return [date_range_str]


def collect_kpi_data(
    config_reader: ConfigReader,
    bot_token: str,
    dates: List[str]
) -> Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]:
    """
    Collect KPI data for all products, environments, and dates.

    Returns:
        Dict structure: {product: {environment: {date: {kpis}}}}
    """
    kpi_data = {}

    # Get all products
    products = config_reader.get_product_names()

    print(f"\n=== Collecting KPI Data ===")
    print(f"Products: {', '.join(products)}")
    print(f"Date range: {dates[0]} to {dates[-1]} ({len(dates)} days)")
    print()

    for product in products:
        print(f"Processing product: {product}")
        kpi_data[product] = {}

        # Get product configuration
        product_config = config_reader.get_product_config(product)
        if not product_config:
            print(f"  Warning: Could not load configuration for product {product}")
            continue

        # Get all environments for this product
        environments = config_reader.get_environment_names(product)

        for environment in environments:
            print(f"  Environment: {environment}")
            kpi_data[product][environment] = {}

            # Get Slack channel ID
            slack_channel_id = product_config.get_slack_channel_id(environment)
            if not slack_channel_id:
                print(f"    Warning: No Slack channel ID for {product}/{environment}")
                continue

            for date_str in dates:
                print(f"    Processing date: {date_str}... ", end='', flush=True)

                try:
                    # Get time window for this date
                    oldest, latest = get_evening_window(date_str)

                    # Create analyzer parameters
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

                    # Fetch messages from main channel
                    messages = fetch_slack_messages(slack_channel_id, bot_token, oldest, latest)

                    # If prod environment and oncall channel is different, fetch from oncall too
                    if environment == 'prod' and product_config.oncall_config:
                        oncall_channel_id = product_config.oncall_config.channel_id
                        if oncall_channel_id and oncall_channel_id != slack_channel_id:
                            from analyzer.slack.parser_provider import SlackMessageParserProvider

                            oncall_messages_raw = fetch_slack_messages(oncall_channel_id, bot_token, oldest, latest)

                            # Filter oncall messages
                            parser_provider = SlackMessageParserProvider()
                            oncall_parser = parser_provider.get_parser(product, environment, product_config.oncall_config)

                            oncall_alarm_messages = []
                            for msg in oncall_messages_raw:
                                alarm_info = oncall_parser.extract_alarm_info(msg)
                                if alarm_info:
                                    alarm_name = alarm_info.get('name', '')
                                    if product_config.oncall_config.is_oncall_alarm(alarm_name):
                                        oncall_alarm_messages.append(msg)

                            messages.extend(oncall_alarm_messages)

                    # Analyze alarms
                    alarm_stats, analyzable_alarms, total_alarms, ignored_messages, oncall_total, oncall_in_reperibilita = analyze_alarms(messages, analyzer_params)

                    # Store KPIs
                    kpi_data[product][environment][date_str] = {
                        'total_alarms': total_alarms,
                        'analyzable_alarms': analyzable_alarms,
                        'ignored_alarms': len(ignored_messages),
                        'oncall_total': oncall_total if environment == 'prod' else None,
                        'oncall_in_reperibilita': oncall_in_reperibilita if environment == 'prod' else None
                    }

                    print(f"✓ (Total: {total_alarms}, Analyzable: {analyzable_alarms}, OnCall: {oncall_total if environment == 'prod' else 'N/A'})")

                except SlackAPIError as e:
                    print(f"✗ Slack API error: {e}")
                    kpi_data[product][environment][date_str] = None
                except Exception as e:
                    print(f"✗ Error: {e}")
                    kpi_data[product][environment][date_str] = None

        print()

    return kpi_data


def parse_arguments():
    """Parse command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python kpi_report.py <date_range> [report=formats]")
        print()
        print("Date range formats:")
        print("  Single date: DD-MM-YY (e.g., 19-09-25)")
        print("  Date range: DD-MM-YY:DD-MM-YY (e.g., 19-09-25:21-09-25)")
        print()
        print("Examples:")
        print("  python kpi_report.py 19-09-25")
        print("  python kpi_report.py 19-09-25:21-09-25")
        print("  python kpi_report.py 19-09-25:21-09-25 report=html")
        print("  python kpi_report.py 19-09-25:21-09-25 report=html,pdf")
        print()
        print("Report formats: html, pdf, csv (default: html)")
        sys.exit(1)

    date_range_str = sys.argv[1]

    # Define valid formats
    valid_formats = {
        'html': {'class': 'KpiHtmlReporter', 'module': 'analyzer.reporting.kpi_html_reporter'},
        'pdf': {'class': 'KpiPdfReporter', 'module': 'analyzer.reporting.kpi_pdf_reporter'},
        'csv': {'class': 'KpiCsvReporter', 'module': 'analyzer.reporting.kpi_csv_reporter'}
    }

    # Parse report formats
    report_formats = ['html']  # Default

    for i in range(2, len(sys.argv)):
        arg = sys.argv[i]
        if arg.startswith('report='):
            formats_str = arg.split('=', 1)[1]
            report_formats = [fmt.strip() for fmt in formats_str.split(',')]

            # Validate report formats
            invalid_formats = [fmt for fmt in report_formats if fmt not in valid_formats]
            if invalid_formats:
                print(f"Error: Invalid report format(s): {', '.join(invalid_formats)}")
                print(f"Valid formats are: {', '.join(sorted(valid_formats.keys()))}")
                sys.exit(1)

    return date_range_str, report_formats, valid_formats


def main():
    date_range_str, report_formats, valid_formats = parse_arguments()

    # Parse date range
    try:
        dates = parse_date_range(date_range_str)
    except ValueError as e:
        print(f"Date parsing error: {e}")
        sys.exit(1)

    # Load configuration
    try:
        config_reader = ConfigReader()
        config_reader.load_config()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Read Slack token
    load_dotenv()
    bot_token = os.getenv('SLACK_TOKEN')
    if not bot_token:
        print("Error: SLACK_TOKEN environment variable not set")
        sys.exit(1)

    # Collect KPI data
    kpi_data = collect_kpi_data(config_reader, bot_token, dates)

    # Generate reports
    print("\n=== Generating Reports ===")
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
            report_path = reporter.generate_report(kpi_data, dates, date_range_str)
            print(f"{format_name.upper()} report generated at: {report_path}")

        except ImportError as e:
            print(f"{format_name.upper()} report generation failed: Module not found - {e}")
        except Exception as e:
            print(f"{format_name.upper()} report generation failed: {e}")


if __name__ == "__main__":
    main()
