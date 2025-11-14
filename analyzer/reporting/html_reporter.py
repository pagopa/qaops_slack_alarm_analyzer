import os
import tempfile
from datetime import datetime
from typing import Dict, Any, List
from collections import Counter
from jinja2 import Environment, FileSystemLoader, select_autoescape
import weasyprint
from ..analyzer_params import AnalyzerParams
from ..duration_params import DurationParams
from .reporter import Reporter


def get_report_filepath(params: AnalyzerParams):
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    filename = f"alarm_report_{params.product}_{params.environment}_{params.date_str_safe}.html"
    return os.path.join(reports_dir, filename)


class HtmlReporter:
    """HTML report generator using Jinja2 templates."""

    def generate_report(self, alarm_stats: Dict[str, Any], analyzed_alarms: int, total_alarms: int, analyzer_params: AnalyzerParams, ignored_messages: List[Dict[str, Any]]) -> str:
        """Generate HTML report using Jinja2 template."""
        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Add custom filter for hourly distribution
        def hourly_distribution_filter(alarm_entries):
            """Custom filter to generate hourly distribution for alarms."""
            timestamps = [alarm['timestamp'] for alarm in alarm_entries if alarm.get('timestamp')]
            hours = [ts.hour for ts in timestamps if ts]
            hour_counts = Counter(hours)

            result = []
            for hour in range(24):
                count = hour_counts.get(hour, 0)
                if count > 0:
                    if count <= 2:
                        icon = "🔹"
                    elif count <= 5:
                        icon = "🔸"
                    elif count <= 9:
                        icon = "🔺"
                    else:
                        icon = "🔥"
                    time_range = f"{hour:02d}:00–{(hour + 1) % 24:02d}:00"
                    result.append(f"{time_range} ({count}) {icon}")

            return result

        env.filters['hourly_distribution'] = hourly_distribution_filter

        # Load template
        template = env.get_template('html_report.html')

        # Prepare alarm stats sorted by count (descending)
        alarm_stats_sorted = sorted(alarm_stats.items(), key=lambda x: len(x[1]), reverse=True) if alarm_stats else []

        # Render template
        html_content = template.render(
            date_str=analyzer_params.date_str,
            product=analyzer_params.product,
            environment_upper=analyzer_params.environment_upper,
            total_alarms=total_alarms,
            analyzed_alarms=analyzed_alarms,
            ignored_count=len(ignored_messages) if ignored_messages else 0,
            alarm_stats_sorted=alarm_stats_sorted,
            ignored_messages=ignored_messages
        )

        # Save to file
        report_path = get_report_filepath(analyzer_params)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return report_path

    def generate_open_duration_report(self, params: DurationParams):
        """Generate open duration report using Jinja2 template with same styling as regular reports."""
        # Create Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Load template
        template = env.get_template('open_duration_report.html')

        # Prepare data for template
        from_str = datetime.fromtimestamp(params.oldest).strftime('%Y-%m-%d %H:%M:%S')
        to_str = datetime.fromtimestamp(params.latest).strftime('%Y-%m-%d %H:%M:%S')

        # Ensure durations are sorted by longest open first (same logic as open_duration.py)
        from datetime import timezone
        now = datetime.now(timezone.utc).timestamp()
        sorted_durations = sorted(
            params.durations,
            key=lambda x: x[4] if x[4] is not None else now - x[2],  # x[4] is duration, x[2] is open_ts
            reverse=True  # Longest durations first
        )

        # Process durations with formatted data
        processed_durations = []
        for alarm_id, alarm_name, open_ts, close_ts, duration in sorted_durations:
            open_time = datetime.fromtimestamp(open_ts).strftime('%Y-%m-%d %H:%M:%S')

            if close_ts:
                close_time = datetime.fromtimestamp(close_ts).strftime('%Y-%m-%d %H:%M:%S')
                is_still_open = False
                # Use the provided duration for closed alarms
                actual_duration = duration
            else:
                close_time = "STILL OPEN"
                is_still_open = True
                # Calculate actual duration for still open alarms
                actual_duration = now - open_ts

            # Format duration (using actual duration for both open and closed)
            if actual_duration >= 3600:
                dur_str = f"{actual_duration / 3600:.0f} hours"
            else:
                dur_str = f"{actual_duration / 60:.0f} minutes"

            processed_durations.append({
                'alarm_id': alarm_id,
                'alarm_name': alarm_name,
                'open_time': open_time,
                'close_time': close_time,
                'duration_str': dur_str,
                'is_still_open': is_still_open,
                'duration_seconds': actual_duration
            })

        # Render template
        html_content = template.render(
            date_str=params.date_str,
            days_back=params.days_back,
            from_str=from_str,
            to_str=to_str,
            num_messages=params.num_messages,
            num_openings=params.num_openings,
            num_closings=params.num_closings,
            durations=processed_durations
        )

        # Save to file
        os.makedirs("reports", exist_ok=True)
        report_filename = f"duration_report_{params.date_str_safe}.html"
        report_path = os.path.join("reports", report_filename)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return report_path