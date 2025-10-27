"""
CSV report generator for QAOps Slack Alarm Analyzer.
Exports alarm statistics and ignored messages to CSV format.
"""
import os
import csv
from datetime import datetime
from typing import Dict, Any, List
from collections import Counter
from ..analyzer_params import AnalyzerParams
from ..duration_params import DurationParams
from .reporter import Reporter


class CsvReporter:
    """CSV report generator that exports alarm data to CSV format."""

    def __init__(self):
        """Initialize CSV reporter."""
        pass

    def generate_report(
        self,
        alarm_stats: Dict[str, Any],
        total_alarms: int,
        analyzer_params: AnalyzerParams,
        ignored_messages: List[Dict[str, Any]]
    ) -> str:
        """
        Generate CSV reports for alarm statistics and ignored messages.

        Args:
            alarm_stats: Dictionary containing alarm statistics
            total_alarms: Total number of alarm messages
            analyzer_params: Analysis parameters containing configuration
            ignored_messages: List of messages that were ignored

        Returns:
            str: Path to the main alarm statistics CSV file
        """
        # Generate main alarm statistics CSV
        alarm_csv_path = self._generate_alarm_statistics_csv(alarm_stats, analyzer_params)

        # Generate ignored messages CSV if there are any
        if ignored_messages:
            ignored_csv_path = self._generate_ignored_messages_csv(ignored_messages, analyzer_params)
            print(f"Ignored messages CSV generated at: {ignored_csv_path}")

        # Generate summary CSV with overall statistics
        summary_csv_path = self._generate_summary_csv(alarm_stats, total_alarms, ignored_messages, analyzer_params)
        print(f"Summary CSV generated at: {summary_csv_path}")

        return alarm_csv_path

    def _generate_alarm_statistics_csv(
        self,
        alarm_stats: Dict[str, Any],
        analyzer_params: AnalyzerParams
    ) -> str:
        """Generate CSV file with detailed alarm statistics."""
        csv_path = self._get_csv_filepath(analyzer_params, "alarm_statistics")

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'alarm_name',
                'total_count',
                'first_occurrence',
                'last_occurrence',
                'most_active_hour',
                'hourly_distribution',
                'alarm_ids',
                'timestamps'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Sort alarms by count (descending)
            sorted_alarms = sorted(alarm_stats.items(), key=lambda x: len(x[1]), reverse=True)

            for alarm_name, alarm_entries in sorted_alarms:
                # Calculate statistics for this alarm
                count = len(alarm_entries)
                timestamps = [alarm['timestamp'] for alarm in alarm_entries if alarm.get('timestamp')]
                alarm_ids = [alarm['id'] for alarm in alarm_entries if alarm.get('id')]

                # Find first and last occurrences
                first_occurrence = min(timestamps).strftime('%Y-%m-%d %H:%M:%S') if timestamps else 'N/A'
                last_occurrence = max(timestamps).strftime('%Y-%m-%d %H:%M:%S') if timestamps else 'N/A'

                # Calculate hourly distribution
                hours = [ts.hour for ts in timestamps if ts]
                hour_counts = Counter(hours)
                most_active_hour = hour_counts.most_common(1)[0][0] if hour_counts else 'N/A'

                # Create hourly distribution string
                hourly_dist_parts = []
                for hour in range(24):
                    count_hour = hour_counts.get(hour, 0)
                    if count_hour > 0:
                        hourly_dist_parts.append(f"{hour:02d}:00-{(hour+1)%24:02d}:00({count_hour})")

                hourly_distribution = "; ".join(hourly_dist_parts) if hourly_dist_parts else 'No data'

                # Create formatted lists for IDs and timestamps
                alarm_ids_str = "; ".join(alarm_ids) if alarm_ids else 'N/A'
                timestamps_str = "; ".join([ts.strftime('%Y-%m-%d %H:%M:%S') for ts in timestamps]) if timestamps else 'N/A'

                writer.writerow({
                    'alarm_name': alarm_name,
                    'total_count': count,
                    'first_occurrence': first_occurrence,
                    'last_occurrence': last_occurrence,
                    'most_active_hour': f"{most_active_hour:02d}:00" if isinstance(most_active_hour, int) else most_active_hour,
                    'hourly_distribution': hourly_distribution,
                    'alarm_ids': alarm_ids_str,
                    'timestamps': timestamps_str
                })

        return csv_path

    def _generate_ignored_messages_csv(
        self,
        ignored_messages: List[Dict[str, Any]],
        analyzer_params: AnalyzerParams
    ) -> str:
        """Generate CSV file with ignored messages details."""
        csv_path = self._get_csv_filepath(analyzer_params, "ignored_messages")

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'timestamp',
                'reason',
                'message_type',
                'text_content',
                'title',
                'fallback',
                'file_name',
                'file_text_preview'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for ignored in ignored_messages:
                # Extract content safely
                timestamp_str = ignored['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if ignored.get('timestamp') else 'N/A'

                # Determine message type based on available fields
                message_type = 'Unknown'
                if ignored.get('file_name'):
                    message_type = 'File Attachment'
                elif ignored.get('text'):
                    message_type = 'Text Message'
                elif ignored.get('title'):
                    message_type = 'Titled Message'

                # Truncate long text fields for CSV readability
                text_content = (ignored.get('text', '')[:200] + '...' if len(ignored.get('text', '')) > 200 else ignored.get('text', ''))
                file_text_preview = (ignored.get('file_text', '')[:200] + '...' if len(ignored.get('file_text', '')) > 200 else ignored.get('file_text', ''))

                writer.writerow({
                    'timestamp': timestamp_str,
                    'reason': ignored.get('reason', 'No reason provided'),
                    'message_type': message_type,
                    'text_content': text_content,
                    'title': ignored.get('title', ''),
                    'fallback': ignored.get('fallback', ''),
                    'file_name': ignored.get('file_name', ''),
                    'file_text_preview': file_text_preview
                })

        return csv_path

    def _generate_summary_csv(
        self,
        alarm_stats: Dict[str, Any],
        total_alarms: int,
        ignored_messages: List[Dict[str, Any]],
        analyzer_params: AnalyzerParams
    ) -> str:
        """Generate CSV file with summary statistics."""
        csv_path = self._get_csv_filepath(analyzer_params, "summary")

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'metric',
                'value',
                'description'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Basic statistics
            unique_alarms = len(alarm_stats) if alarm_stats else 0
            ignored_count = len(ignored_messages) if ignored_messages else 0

            # Calculate additional statistics
            if alarm_stats:
                # Find most frequent alarm
                sorted_alarms = sorted(alarm_stats.items(), key=lambda x: len(x[1]), reverse=True)
                most_frequent_alarm = sorted_alarms[0][0] if sorted_alarms else 'N/A'
                most_frequent_count = len(sorted_alarms[0][1]) if sorted_alarms else 0

                # Calculate average alarms per type
                avg_alarms_per_type = total_alarms / unique_alarms if unique_alarms > 0 else 0

                # Find peak hour across all alarms
                all_timestamps = []
                for alarm_entries in alarm_stats.values():
                    all_timestamps.extend([alarm['timestamp'] for alarm in alarm_entries if alarm.get('timestamp')])

                hours = [ts.hour for ts in all_timestamps if ts]
                hour_counts = Counter(hours)
                peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 'N/A'
                peak_hour_count = hour_counts.most_common(1)[0][1] if hour_counts else 0
            else:
                most_frequent_alarm = 'N/A'
                most_frequent_count = 0
                avg_alarms_per_type = 0
                peak_hour = 'N/A'
                peak_hour_count = 0

            # Write summary rows
            summary_data = [
                ('total_alarms', total_alarms, 'Total number of alarm messages'),
                ('unique_alarm_types', unique_alarms, 'Number of different alarm types'),
                ('ignored_messages', ignored_count, 'Number of ignored messages'),
                ('most_frequent_alarm', most_frequent_alarm, 'Alarm type with highest occurrence count'),
                ('most_frequent_count', most_frequent_count, 'Occurrence count of most frequent alarm'),
                ('avg_alarms_per_type', f"{avg_alarms_per_type:.2f}", 'Average alarms per alarm type'),
                ('peak_hour', f"{peak_hour:02d}:00" if isinstance(peak_hour, int) else peak_hour, 'Hour with most alarm activity'),
                ('peak_hour_count', peak_hour_count, 'Number of alarms in peak hour'),
                ('analysis_date', analyzer_params.date_str, 'Date of analysis'),
                ('product', analyzer_params.product, 'Product analyzed'),
                ('environment', analyzer_params.environment, 'Environment analyzed')
            ]

            for metric, value, description in summary_data:
                writer.writerow({
                    'metric': metric,
                    'value': value,
                    'description': description
                })

        return csv_path

    def _get_csv_filepath(self, analyzer_params: AnalyzerParams, report_type: str) -> str:
        """Generate the CSV file path for a specific report type."""
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        filename = f"alarm_report_{analyzer_params.product}_{analyzer_params.environment}_{analyzer_params.date_str_safe}_{report_type}.csv"
        return os.path.join(reports_dir, filename)

    def generate_open_duration_report(self, params: DurationParams) -> str:
        """
        Generate CSV report for alarm durations (open/close times).

        Args:
            params: Duration analysis parameters

        Returns:
            str: Path to the generated CSV file
        """
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        csv_filename = f"duration_report_{params.date_str_safe}.csv"
        csv_path = os.path.join(reports_dir, csv_filename)

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'alarm_id',
                'alarm_name',
                'opened_at',
                'closed_at',
                'status',
                'duration_seconds',
                'duration_formatted'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Sort durations by longest open first (same logic as HTML/PDF reporters)
            from datetime import timezone
            now = datetime.now(timezone.utc).timestamp()
            sorted_durations = sorted(
                params.durations,
                key=lambda x: x[4] if x[4] is not None else now - x[2],
                reverse=True
            )

            for alarm_id, alarm_name, open_ts, close_ts, duration in sorted_durations:
                # Format timestamps
                open_time = datetime.fromtimestamp(open_ts).strftime('%Y-%m-%d %H:%M:%S')

                if close_ts:
                    close_time = datetime.fromtimestamp(close_ts).strftime('%Y-%m-%d %H:%M:%S')
                    status = 'CLOSED'
                    actual_duration = duration
                else:
                    close_time = ''
                    status = 'STILL OPEN'
                    actual_duration = now - open_ts

                # Format duration
                if actual_duration >= 3600:
                    duration_formatted = f"{actual_duration / 3600:.2f} hours"
                else:
                    duration_formatted = f"{actual_duration / 60:.2f} minutes"

                writer.writerow({
                    'alarm_id': alarm_id,
                    'alarm_name': alarm_name,
                    'opened_at': open_time,
                    'closed_at': close_time,
                    'status': status,
                    'duration_seconds': f"{actual_duration:.2f}",
                    'duration_formatted': duration_formatted
                })

        return csv_path