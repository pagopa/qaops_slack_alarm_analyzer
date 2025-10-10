import os
from datetime import datetime
from typing import Dict, Any, List
from collections import Counter
from jinja2 import Environment, FileSystemLoader
from ..analyzer_params import AnalyzerParams
from .reporter import Reporter

def generate_alarm_statistics_html(alarm_stats, date_str):
    """Generate HTML summary statistics of alarms in table format."""
    if not alarm_stats:
        return "<p>No alarms found.</p>"

    html = []
    html.append(f"<h2>Alarm Statistics Summary</h2>")
    html.append("<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; width: 100%; margin-bottom: 20px;'>")
    html.append("<thead>")
    html.append("<tr style='background-color: #f0f0f0;'>")
    html.append("<th style='text-align: left;'>Alarm Name</th>")
    html.append("<th style='text-align: center;'>Count</th>")
    html.append("<th style='text-align: left;'>Recent Occurrences</th>")
    html.append("<th style='text-align: left;'>Hourly Distribution</th>")
    html.append("</tr>")
    html.append("</thead>")
    html.append("<tbody>")

    sorted_alarms = sorted(alarm_stats.items(), key=lambda x: len(x[1]), reverse=True)

    for alarm_name, alarm_entries in sorted_alarms:
        count = len(alarm_entries)

        # Generate recent occurrences list
        recent_ids = []
        for alarm in alarm_entries[:]:  # Show up to 5 recent occurrences
            timestamp_str = alarm['timestamp'].strftime('%d-%m %H:%M')
            recent_ids.append(f"#{alarm['id']} ({timestamp_str})")

        ids_str = '<br>'.join(recent_ids)

        # Generate hourly distribution
        timestamps = [alarm['timestamp'] for alarm in alarm_entries]
        hourly_dist = generate_compact_hourly_distribution_html(timestamps)

        # Add row to table
        html.append("<tr>")
        html.append(f"<td style='vertical-align: top; font-weight: bold;'>{alarm_name}</td>")
        html.append(f"<td style='vertical-align: top; text-align: center; font-size: 18px; font-weight: bold; color: #d73527;'>{count}</td>")
        html.append(f"<td style='vertical-align: top; font-family: monospace; font-size: 12px;'>{ids_str}</td>")
        html.append(f"<td style='vertical-align: top;'>{hourly_dist}</td>")
        html.append("</tr>")

    html.append("</tbody>")
    html.append("</table>")
    return "\n".join(html)

def generate_compact_hourly_distribution_html(timestamps):
    """Generate compact HTML for 24-hour distribution."""
    from collections import Counter
    hours = [ts.hour for ts in timestamps if ts]
    hour_counts = Counter(hours)

    if not hour_counts:
        return "<em>No time data</em>"

    # Create a compact visual representation
    html = []
    html.append("<div style='font-size: 14px;'>")

    active_hours = []
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
            active_hours.append(f"{time_range} ({count}) {icon}")

    if active_hours:
        # Stack vertically, one per line
        for hour_info in active_hours:
            html.append(f"<div>{hour_info}</div>")
    else:
        html.append("<em>No activity</em>")

    html.append("</div>")
    return "\n".join(html)

def generate_hourly_distribution_html(timestamps):
    """Generate HTML for 24-hour distribution histogram (full table)."""
    from collections import Counter
    hours = [ts.hour for ts in timestamps if ts]
    hour_counts = Counter(hours)

    html = []
    html.append("<table>")
    html.append("<thead><tr><th>Hour</th><th>Occurrences</th><th>Visual</th></tr></thead>")
    html.append("<tbody>")

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

        html.append(f"<tr><td>{hour:02d}:00–{(hour + 1) % 24:02d}:00</td><td>{count}</td><td>{icon}</td></tr>")

    html.append("</tbody></table>")
    return "\n".join(html)

def get_report_filepath(params: AnalyzerParams):
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    filename = f"alarm_report_{params.product}_{params.environment}_{params.date_str}.html"
    return os.path.join(reports_dir, filename)

def generate_ignored_alarms_html(ignored_messages):
    """Generate HTML table for ignored alarm messages."""
    if not ignored_messages:
        return "<p>No messages were ignored.</p>"

    html = []
    html.append(f"<h2>Ignored Messages ({len(ignored_messages)} total)</h2>")
    html.append("<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse; width: 100%;'>")
    html.append("<thead>")
    html.append("<tr style='background-color: #f0f0f0;'>")
    html.append("<th>Timestamp</th>")
    html.append("<th>Reason</th>")
    html.append("<th>Content</th>")
    html.append("</tr>")
    html.append("</thead>")
    html.append("<tbody>")

    for ignored in ignored_messages:
        timestamp_str = ignored['timestamp'].strftime('%d-%m-%Y %H:%M:%S') if ignored['timestamp'] else 'N/A'

        # Construct content preview
        content_parts = []
        if ignored.get('text'):
            content_parts.append(f"Text: {ignored['text'][:100]}{'...' if len(ignored['text']) > 100 else ''}")
        if ignored.get('title'):
            content_parts.append(f"Title: {ignored['title'][:100]}{'...' if len(ignored['title']) > 100 else ''}")
        if ignored.get('fallback'):
            content_parts.append(f"Fallback: {ignored['fallback'][:100]}{'...' if len(ignored['fallback']) > 100 else ''}")
        if ignored.get('file_name'):
            content_parts.append(f"File: {ignored['file_name']}")
        if ignored.get('file_text'):
            content_parts.append(f"File content: {ignored['file_text']}")

        content = '<br>'.join(content_parts) if content_parts else 'No content available'

        html.append("<tr>")
        html.append(f"<td>{timestamp_str}</td>")
        html.append(f"<td>{ignored['reason']}</td>")
        html.append(f"<td>{content}</td>")
        html.append("</tr>")

    html.append("</tbody>")
    html.append("</table>")
    return "\n".join(html)

class HtmlReporter:
    """HTML report generator using Jinja2 templates."""

    def generate_report(self, alarm_stats: Dict[str, Any], total_alarms: int, analyzer_params: AnalyzerParams, ignored_messages: List[Dict[str, Any]]) -> str:
        """Generate HTML report using Jinja2 template."""
        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))

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
            alarm_stats_sorted=alarm_stats_sorted,
            ignored_messages=ignored_messages
        )

        # Save to file
        report_path = get_report_filepath(analyzer_params)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return report_path


def generate_html_report(alarm_stats, total_alarms, params: AnalyzerParams, ignored_messages=None):
    """Generate HTML report using HtmlReporter class with Jinja2 template."""
    reporter = HtmlReporter()
    return reporter.generate_report(alarm_stats, total_alarms, params, ignored_messages)


def generate_duration_report(durations, date_str, days_back, oldest, latest, num_messages, num_openings, num_closings):
    os.makedirs("reports", exist_ok=True)
    report_filename = f"duration_report_{date_str}.html"
    report_path = os.path.join("reports", report_filename)

    from_str = datetime.fromtimestamp(oldest).strftime('%Y-%m-%d %H:%M:%S')
    to_str = datetime.fromtimestamp(latest).strftime('%Y-%m-%d %H:%M:%S')

    with open(report_path, "w") as f:
        f.write("<html><head><meta charset='UTF-8'><title>Alarm Duration Report</title></head><body>")
        f.write(f"<h1>Alarm Duration Report - {date_str}</h1>")

        # Intestazione dettagliata
        f.write("<pre>")
        f.write(f"Fetching messages from the last {days_back} day(s)...\n")
        f.write(f"from:  {from_str}\n")
        f.write(f"to:    {to_str}\n")
        f.write(f"Fetched {num_messages} messages\n")
        f.write(f"openings {num_openings} openings\n")
        f.write(f"closings {num_closings} closings\n")
        f.write("</pre>")

        # Tabella
        f.write("<h2>Alarm Durations (longest open first)</h2>")
        f.write("<table border='1' cellpadding='5' cellspacing='0'>")
        f.write("<tr><th>Alarm Name</th><th>Alarm ID</th><th>Opened</th><th>Closed</th><th>Duration</th></tr>")

        for alarm_id, alarm_name, open_ts, close_ts, duration in durations:
            open_time = datetime.fromtimestamp(open_ts).strftime('%Y-%m-%d %H:%M:%S')
            dur_str = f"{duration / 3600:.0f} hours" if duration >= 3600 else f"{duration / 60:.0f} minutes"
            
            if close_ts:
                close_time = datetime.fromtimestamp(close_ts).strftime('%Y-%m-%d %H:%M:%S')
            else:
                close_time = "STILL OPEN"

            f.write(f"<tr><td>{alarm_name}</td><td>{alarm_id}</td><td>{open_time}</td><td>{close_time}</td><td>{dur_str}</td></tr>")

        f.write("</table></body></html>")

    return report_path