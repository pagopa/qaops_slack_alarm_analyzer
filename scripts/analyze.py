from dotenv import load_dotenv
from datetime import datetime
import os
import sys
import warnings

# Suppress urllib3 warning about OpenSSL version
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

from analyzer.slack import fetch_slack_messages, SlackAPIError
from analyzer.alarm_parser import analyze_alarms
from analyzer.reporting import generate_html_report
from analyzer.utils import get_evening_window
from analyzer.config.config_reader import ConfigReader
from analyzer.analyzer_params import AnalyzerParams

def main():
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python analyze.py <date> <product> [environment]")
        print("Examples:")
        print("  python analyze.py 19-09-25 SEND")
        print("  python analyze.py 19-09-25 SEND prod")
        print("  python analyze.py 19-09-25 INTEROP test")
        sys.exit(1)

    date_str = sys.argv[1]
    product = sys.argv[2].upper()
    environment = sys.argv[3] if len(sys.argv) == 4 else 'prod'

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

    try:
        oldest, latest = get_evening_window(date_str)
    except ValueError as e:
        print(f"Date parsing error: {e}")
        sys.exit(1)

    # Create analyzer parameters
    try:
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
        print(f"Parameter validation error: {e}")
        sys.exit(1)

    print(f"\n=== Alarm Statistics ===")
    print("Start window: ", datetime.fromtimestamp(oldest).strftime('%Y-%m-%d %H:%M:%S'))
    print("End window:", datetime.fromtimestamp(latest).strftime('%Y-%m-%d %H:%M:%S'))
    print(f"Analyzing alarm for product: {product}")
    print(f"Environment: {environment}")
    print(f"Channel ID: {slack_channel_id}")

    try:
        messages = fetch_slack_messages(slack_channel_id, bot_token, oldest, latest)
    except SlackAPIError as e:
        print(f"Slack API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Network or HTTP error: {e}")
        sys.exit(1)

    alarm_stats, total_alarms, ignored_messages = analyze_alarms(messages, analyzer_params)
    print(f"Total alarm messages: {total_alarms}")

    report_path = generate_html_report(alarm_stats, total_alarms, analyzer_params, ignored_messages)
    print(f"Report generated at: {report_path}")

if __name__ == "__main__":
    main()