import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, List
import weasyprint
from jinja2 import Environment, FileSystemLoader, select_autoescape
from collections import Counter
from ..analyzer_params import AnalyzerParams
from ..duration_params import DurationParams
from .reporter import Reporter


def format_time_constraint(constraint) -> List[str]:
    """Format a TimeConstraint object into human-readable text lines.

    Args:
        constraint: TimeConstraint object or None

    Returns:
        List of formatted strings describing the constraint
    """
    if not constraint or constraint.is_empty():
        return []

    lines = []

    # Format periods
    if constraint.periods:
        for period in constraint.periods:
            start_str = period.start.strftime("%Y-%m-%d") if period.start else "∞"
            end_str = period.end.strftime("%Y-%m-%d") if period.end else "∞"
            lines.append(f"Period: {start_str} → {end_str}")

    # Format weekdays
    if constraint.weekdays:
        weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        days = [weekday_names[day] for day in sorted(constraint.weekdays)]
        lines.append(f"Weekdays: {', '.join(days)}")

    # Format hours
    if constraint.hours:
        hour_ranges = [str(h) for h in constraint.hours]
        lines.append(f"Hours: {', '.join(hour_ranges)}")

    return lines


def group_ignored_messages_by_name(ignored_messages: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Group ignored messages by alarm name and aggregate information.

    Returns:
        Dict with alarm name as key and dict containing:
            - 'count': number of occurrences
            - 'reason': ignore reason (same for all occurrences of same alarm)
            - 'validity': TimeConstraint for when rule is valid (or None)
            - 'exclusions': TimeConstraint for when rule is excluded (or None)
            - 'occurrences': list of individual occurrences with id and timestamp
    """
    grouped = {}
    for ignored in ignored_messages:
        alarm_name = ignored.get('name', 'Unknown')

        if alarm_name not in grouped:
            grouped[alarm_name] = {
                'count': 0,
                'reason': ignored.get('reason', 'No reason provided'),
                'validity': ignored.get('validity'),
                'exclusions': ignored.get('exclusions'),
                'occurrences': []
            }

        grouped[alarm_name]['count'] += 1
        grouped[alarm_name]['occurrences'].append({
            'id': ignored.get('id', 'N/A'),
            'timestamp': ignored.get('timestamp')
        })

    # Sort occurrences by timestamp (most recent first) for each alarm
    for alarm_data in grouped.values():
        alarm_data['occurrences'].sort(
            key=lambda x: x['timestamp'] if x['timestamp'] else datetime.min,
            reverse=True
        )

    return grouped


class PdfReporter:
    def __init__(self):
        pass

    def generate_report(
        self,
        alarm_stats: Dict[str, Any],
        analyzed_alarms: int,
        total_alarms: int,
        analyzer_params: AnalyzerParams,
        ignored_messages: List[Dict[str, Any]]
    ) -> str:
        # First generate HTML content using existing HTML reporter
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_html:
            html_content = self._generate_html_content(alarm_stats, analyzed_alarms, total_alarms, analyzer_params, ignored_messages)
            temp_html.write(html_content)
            temp_html_path = temp_html.name

        try:
            # Generate PDF from HTML using WeasyPrint
            pdf_path = self._get_pdf_filepath(analyzer_params)
            weasyprint.HTML(filename=temp_html_path).write_pdf(pdf_path)
            return pdf_path
        finally:
            # Clean up temporary HTML file
            if os.path.exists(temp_html_path):
                os.unlink(temp_html_path)

    def _generate_html_content(
        self,
        alarm_stats: Dict[str, Any],
        analyzed_alarms: int,
        total_alarms: int,
        analyzer_params: AnalyzerParams,
        ignored_messages: List[Dict[str, Any]]
    ) -> str:
        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Add custom filters
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
        env.filters['format_time_constraint'] = format_time_constraint

        # Load template
        template = env.get_template('pdf_report.html')

        # Prepare alarm stats sorted by count (descending)
        alarm_stats_sorted = sorted(alarm_stats.items(), key=lambda x: len(x[1]), reverse=True) if alarm_stats else []

        # Group and sort ignored messages by name and count
        ignored_grouped = group_ignored_messages_by_name(ignored_messages) if ignored_messages else {}
        ignored_stats_sorted = sorted(ignored_grouped.items(), key=lambda x: x[1]['count'], reverse=True)

        # Render template
        html_content = template.render(
            date_str=analyzer_params.date_str,
            product=analyzer_params.product,
            environment_upper=analyzer_params.environment_upper,
            total_alarms=total_alarms,
            analyzed_alarms=analyzed_alarms,
            ignored_count=len(ignored_messages) if ignored_messages else 0,
            alarm_stats_sorted=alarm_stats_sorted,
            ignored_messages=ignored_messages,
            ignored_stats_sorted=ignored_stats_sorted
        )

        return html_content

    def _get_pdf_filepath(self, analyzer_params: AnalyzerParams) -> str:
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        filename = f"alarm_report_{analyzer_params.product}_{analyzer_params.environment}_{analyzer_params.date_str_safe}.pdf"
        return os.path.join(reports_dir, filename)
    
    def generate_open_duration_report(self, params: DurationParams):
        """Generate open duration PDF report using Jinja2 template."""
        # Create Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Load PDF template
        template = env.get_template('pdf_open_duration_report.html')

        # Prepare data for template
        from_str = datetime.fromtimestamp(params.oldest).strftime('%Y-%m-%d %H:%M:%S')
        to_str = datetime.fromtimestamp(params.latest).strftime('%Y-%m-%d %H:%M:%S')

        # Ensure durations are sorted by longest open first
        now = datetime.now(timezone.utc).timestamp()
        sorted_durations = sorted(
            params.durations,
            key=lambda x: x[4] if x[4] is not None else now - x[2],
            reverse=True
        )

        # Process durations with formatted data
        processed_durations = []
        for alarm_id, alarm_name, open_ts, close_ts, duration in sorted_durations:
            open_time = datetime.fromtimestamp(open_ts).strftime('%Y-%m-%d %H:%M:%S')

            if close_ts:
                close_time = datetime.fromtimestamp(close_ts).strftime('%Y-%m-%d %H:%M:%S')
                is_still_open = False
                actual_duration = duration
            else:
                close_time = "STILL OPEN"
                is_still_open = True
                actual_duration = now - open_ts

            # Format duration
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

        # Generate PDF from HTML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_html:
            temp_html.write(html_content)
            temp_html_path = temp_html.name

        try:
            # Create PDF
            os.makedirs("reports", exist_ok=True)
            pdf_filename = f"duration_report_{params.date_str_safe}.pdf"
            pdf_path = os.path.join("reports", pdf_filename)
            weasyprint.HTML(filename=temp_html_path).write_pdf(pdf_path)
            return pdf_path
        finally:
            # Clean up temporary HTML file
            if os.path.exists(temp_html_path):
                os.unlink(temp_html_path)