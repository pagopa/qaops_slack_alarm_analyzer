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
import re
from typing import Dict, Any, List

# Suppress urllib3 warning about OpenSSL version
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

from analyzer.slack import fetch_slack_messages, SlackAPIError, upload_file_to_slack
from analyzer.alarm_parser import analyze_alarms
from analyzer.utils import get_evening_window
from analyzer.config.config_reader import ConfigReader
from analyzer.analyzer_params import AnalyzerParams
from analyzer.alarm_type import build_alarm_types
from analyzer.alarm_analysis_result import merge_analysis_results


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
    dates: List[str],
    products_to_analyze: Dict[str, List[str]]
) -> Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]:
    """
    Collect KPI data for specified products, environments, and dates.

    Args:
        config_reader: Configuration reader instance
        bot_token: Slack bot token
        dates: List of dates to analyze
        products_to_analyze: Dict mapping product to list of environments

    Returns:
        Dict structure: {product: {environment: {date: {kpis}}}}
    """
    kpi_data = {}

    print(f"\n=== Collecting KPI Data ===")
    print(f"Products: {', '.join(products_to_analyze.keys())}")
    print(f"Date range: {dates[0]} to {dates[-1]} ({len(dates)} days)")
    print()

    for product, environments in products_to_analyze.items():
        print(f"Processing product: {product}")
        print(f"  Environments: {', '.join(environments)}")
        kpi_data[product] = {}

        # Get product configuration
        product_config = config_reader.get_product_config(product)
        if not product_config:
            print(f"  Warning: Could not load configuration for product {product}")
            continue

        for environment in environments:
            print(f"  Environment: {environment}")
            kpi_data[product][environment] = {}

            # Get Slack channel ID
            slack_channel_id = product_config.get_slack_channel_id(environment)
            if not slack_channel_id:
                print(f"    Warning: No Slack channel ID for {product}/{environment}")
                continue

            # Build alarm types for this product/environment
            alarm_types = build_alarm_types(product_config, product, environment)
            if not alarm_types:
                print(f"    Warning: No alarm types configured")
                continue

            for date_str in dates:
                print(f"    Processing date: {date_str}... ", end='', flush=True)

                try:
                    # Analyze each alarm type separately
                    analysis_results = []

                    for alarm_type in alarm_types:
                        # Get time window for this alarm type
                        oldest, latest = alarm_type.get_time_window(date_str)

                        # Fetch messages for this alarm type's channel and time window
                        messages = fetch_slack_messages(alarm_type.channel_id, bot_token, oldest, latest)

                        # Analyze alarms for this type
                        result = analyze_alarms(messages, alarm_type, product_config)
                        analysis_results.append(result)

                    # Merge all results
                    merged_result = merge_analysis_results(analysis_results)

                    # Store KPIs
                    kpi_data[product][environment][date_str] = {
                        'total_alarms': merged_result.total_alarms,
                        'analyzable_alarms': merged_result.analyzable_alarms,
                        'ignored_alarms': merged_result.ignored_alarms,
                        'oncall_total': merged_result.oncall_total if environment == 'prod' else None,
                        'oncall_in_reperibilita': merged_result.oncall_in_reperibilita if environment == 'prod' else None
                    }

                    print(f"✓ (Total: {merged_result.total_alarms}, Analyzable: {merged_result.analyzable_alarms}, OnCall: {merged_result.oncall_total if environment == 'prod' else 'N/A'})")

                except SlackAPIError as e:
                    print(f"✗ Slack API error: {e}")
                    kpi_data[product][environment][date_str] = None
                except Exception as e:
                    print(f"✗ Error: {e}")
                    kpi_data[product][environment][date_str] = None

        print()

    return kpi_data


def parse_product_filter(products_str: str) -> Dict[str, List[str]]:
    """
    Parse product filter string with environment specifications.

    Syntax: PRODUCT1:env1:env2,PRODUCT2:env3
    - PRODUCT -> product with all environments
    - PRODUCT:env1:env2 -> product with specific environments (colon-separated)

    Returns:
        Dict[product_name, list_of_environments or None]
        None in list means all environments for that product
    """
    products_dict = {}

    # Split by comma to get individual product specifications
    product_specs = products_str.split(',')

    for spec in product_specs:
        spec = spec.strip()
        if not spec:
            continue

        # Split by colon: first is product, rest are environments
        parts = spec.split(':')
        product_name = parts[0].strip().upper()

        if len(parts) > 1:
            # Environments specified after colon
            envs = [e.strip().lower() for e in parts[1:] if e.strip()]
            products_dict[product_name] = envs
        else:
            # No colon means all environments
            products_dict[product_name] = None

    return products_dict


def parse_arguments():
    """Parse command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python kpi_report.py <date_range> [product=products] [report=formats] [slack=true|false]")
        print()
        print("Date range formats:")
        print("  Single date: DD-MM-YY (e.g., 19-09-25)")
        print("  Date range: DD-MM-YY:DD-MM-YY (e.g., 19-09-25:21-09-25)")
        print()
        print("Optional filters:")
        print("  product=PRODUCT:envs    Specify products with optional environments")
        print("  slack=true|false        Enable/disable Slack publishing (default: false)")
        print()
        print("Product syntax:")
        print("  PRODUCT                 Product with all environments")
        print("  PRODUCT:env1:env2       Product with specific environments (colon-separated)")
        print("  PROD1:env1,PROD2:env2   Multiple products (comma-separated)")
        print()
        print("Examples:")
        print("  python kpi_report.py 19-09-25")
        print("  python kpi_report.py 19-09-25:21-09-25")
        print("  python kpi_report.py 19-09-25:21-09-25 product=SEND")
        print("  python kpi_report.py 19-09-25:21-09-25 product=SEND:prod")
        print("  python kpi_report.py 19-09-25:21-09-25 product=SEND:prod:uat")
        print("  python kpi_report.py 19-09-25:21-09-25 product=SEND,INTEROP")
        print("  python kpi_report.py 19-09-25:21-09-25 product=SEND:prod:uat,INTEROP:prod")
        print("  python kpi_report.py 19-09-25:21-09-25 product=SEND:prod report=pdf slack=true")
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

    # Parse optional parameters
    report_formats = ['html']  # Default
    products_filter = None  # None means all products, Dict[product, [envs]] otherwise
    publish_to_slack = False  # Default: do not publish to Slack

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

        elif arg.startswith('product='):
            products_str = arg.split('=', 1)[1]
            try:
                products_filter = parse_product_filter(products_str)
            except Exception as e:
                print(f"Error parsing product filter: {e}")
                print("Expected syntax: PRODUCT1:env1:env2,PRODUCT2:env3")
                sys.exit(1)

        elif arg.startswith('slack='):
            slack_str = arg.split('=', 1)[1].lower()
            if slack_str in ['true', '1', 'yes']:
                publish_to_slack = True
            elif slack_str in ['false', '0', 'no']:
                publish_to_slack = False
            else:
                print(f"Error: Invalid value for slack parameter: {slack_str}")
                print("Valid values: true, false")
                sys.exit(1)

    return date_range_str, report_formats, valid_formats, products_filter, publish_to_slack


def main():
    date_range_str, report_formats, valid_formats, products_filter, publish_to_slack = parse_arguments()

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

    # Validate and build products_to_analyze dict
    available_products = config_reader.get_product_names()

    if products_filter:
        # Validate products
        invalid_products = [p for p in products_filter.keys() if p not in available_products]
        if invalid_products:
            print(f"Error: Invalid product(s): {', '.join(invalid_products)}")
            print(f"Available products: {', '.join(available_products)}")
            sys.exit(1)

        # Validate environments for each product
        products_to_analyze = {}
        for product, envs in products_filter.items():
            available_envs = config_reader.get_environment_names(product)

            if envs is None:
                # No environments specified, use all
                products_to_analyze[product] = available_envs
            else:
                # Validate specified environments
                invalid_envs = [e for e in envs if e not in available_envs]
                if invalid_envs:
                    print(f"Error: Invalid environment(s) for product {product}: {', '.join(invalid_envs)}")
                    print(f"Available environments for {product}: {', '.join(available_envs)}")
                    sys.exit(1)
                products_to_analyze[product] = envs
    else:
        # No filter specified, use all products with all their environments
        products_to_analyze = {}
        for product in available_products:
            products_to_analyze[product] = config_reader.get_environment_names(product)

    # Read Slack token
    load_dotenv()
    bot_token = os.getenv('SLACK_TOKEN')
    if not bot_token:
        print("Error: SLACK_TOKEN environment variable not set")
        sys.exit(1)

    # Collect KPI data
    kpi_data = collect_kpi_data(config_reader, bot_token, dates, products_to_analyze)

    # Get Slack channel for publishing reports
    reports_channel_id = config_reader.get_kpi_reports_slack_channel_id()

    # Generate reports
    print("\n=== Generating Reports ===")
    generated_reports = []  # Track successfully generated reports for publishing

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

            # Track generated report for publishing
            generated_reports.append({
                'path': report_path,
                'format': format_name
            })

        except ImportError as e:
            print(f"{format_name.upper()} report generation failed: Module not found - {e}")
        except Exception as e:
            print(f"{format_name.upper()} report generation failed: {e}")

    # Publish reports to Slack if enabled and channel is configured
    if publish_to_slack and reports_channel_id and generated_reports:
        print(f"\n=== Publishing Reports to Slack ===")
        print(f"Channel ID: {reports_channel_id}")

        for report_info in generated_reports:
            report_path = report_info['path']
            format_name = report_info['format']

            try:
                # Prepare comment with report summary
                products_list = ', '.join(sorted(products_to_analyze.keys()))
                date_range_display = f"{dates[0]} to {dates[-1]}" if len(dates) > 1 else dates[0]

                initial_comment = (
                    f"*KPI Report* - `{date_range_display}`\n"
                    f"Products: {products_list}\n"
                    f"Period: {len(dates)} day(s)\n\n"
                    f"ℹ️ I valori presenti nel documento servono nelle KPI del foglio *Allarmi*, "
                    f"da utilizzare per riempire i relativi valori o come strumento di verifica dei valori già inseriti."
                )

                # Upload file to Slack
                upload_file_to_slack(
                    file_path=report_path,
                    channel_id=reports_channel_id,
                    bot_token=bot_token,
                    initial_comment=initial_comment,
                    title=f"KPI Report {date_range_display} ({format_name.upper()})"
                )
                print(f"  ✓ {format_name.upper()} report published to Slack")

            except FileNotFoundError as e:
                print(f"  ✗ Failed to publish {format_name.upper()} report: File not found - {e}")
            except SlackAPIError as e:
                print(f"  ✗ Failed to publish {format_name.upper()} report: Slack API error - {e}")
            except Exception as e:
                print(f"  ✗ Failed to publish {format_name.upper()} report: {e}")
    elif publish_to_slack:
        print("\n=== Slack Publishing ===")
        if not reports_channel_id:
            print("Slack channel not configured - skipping report publishing")
        elif not generated_reports:
            print("No reports were generated successfully to publish")
    else:
        print("\n=== Slack Publishing ===")
        print("Slack publishing disabled (use slack=true to enable)")


if __name__ == "__main__":
    main()
