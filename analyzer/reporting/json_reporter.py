"""
JSON report generator for QAOps Slack Alarm Analyzer.
Exports alarm statistics and ignored messages to JSON format.
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List
from collections import Counter
from ..analyzer_params import AnalyzerParams
from .reporter import Reporter


class JsonReporter:
    """JSON report generator that exports alarm data to JSON format."""

    def __init__(self):
        """Initialize JSON reporter."""
        pass

    def generate_report(
        self,
        alarm_stats: Dict[str, Any],
        total_alarms: int,
        analyzer_params: AnalyzerParams,
        ignored_messages: List[Dict[str, Any]]
    ) -> str:
        """
        Generate comprehensive JSON report with all alarm data.

        Args:
            alarm_stats: Dictionary containing alarm statistics
            total_alarms: Total number of alarm messages
            analyzer_params: Analysis parameters containing configuration
            ignored_messages: List of messages that were ignored

        Returns:
            str: Path to the generated JSON file
        """
        # Build comprehensive JSON structure
        report_data = {
            "metadata": self._generate_metadata(analyzer_params, total_alarms, ignored_messages),
            "summary": self._generate_summary_statistics(alarm_stats, total_alarms, ignored_messages, analyzer_params),
            "alarm_statistics": self._generate_alarm_statistics(alarm_stats),
            "hourly_analysis": self._generate_hourly_analysis(alarm_stats),
            "ignored_messages": self._generate_ignored_messages_data(ignored_messages),
            "raw_data": self._generate_raw_data(alarm_stats, ignored_messages)
        }

        # Save to JSON file
        json_path = self._get_json_filepath(analyzer_params)
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(report_data, json_file, indent=2, ensure_ascii=False, default=self._json_serializer)

        return json_path

    def _generate_metadata(
        self,
        analyzer_params: AnalyzerParams,
        total_alarms: int,
        ignored_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate metadata section."""
        return {
            "report_generated_at": datetime.now().isoformat(),
            "analysis_date": analyzer_params.date_str,
            "product": analyzer_params.product,
            "environment": analyzer_params.environment,
            "total_alarms": total_alarms,
            "total_ignored_messages": len(ignored_messages) if ignored_messages else 0,
            "report_version": "1.0",
            "generator": "QAOps Slack Alarm Analyzer - JsonReporter"
        }

    def _generate_summary_statistics(
        self,
        alarm_stats: Dict[str, Any],
        total_alarms: int,
        ignored_messages: List[Dict[str, Any]],
        analyzer_params: AnalyzerParams
    ) -> Dict[str, Any]:
        """Generate summary statistics section."""
        if not alarm_stats:
            return {
                "unique_alarm_types": 0,
                "total_alarms": total_alarms,
                "ignored_messages": len(ignored_messages) if ignored_messages else 0,
                "most_frequent_alarm": None,
                "least_frequent_alarm": None,
                "average_alarms_per_type": 0,
                "peak_hour": None,
                "quietest_hour": None
            }

        # Calculate statistics
        sorted_alarms = sorted(alarm_stats.items(), key=lambda x: len(x[1]), reverse=True)
        unique_alarms = len(alarm_stats)

        most_frequent_alarm = {
            "name": sorted_alarms[0][0],
            "count": len(sorted_alarms[0][1])
        } if sorted_alarms else None

        least_frequent_alarm = {
            "name": sorted_alarms[-1][0],
            "count": len(sorted_alarms[-1][1])
        } if sorted_alarms else None

        avg_alarms_per_type = total_alarms / unique_alarms if unique_alarms > 0 else 0

        # Calculate hourly statistics
        all_timestamps = []
        for alarm_entries in alarm_stats.values():
            all_timestamps.extend([alarm['timestamp'] for alarm in alarm_entries if alarm.get('timestamp')])

        hours = [ts.hour for ts in all_timestamps if ts]
        hour_counts = Counter(hours)

        peak_hour = {
            "hour": hour_counts.most_common(1)[0][0],
            "count": hour_counts.most_common(1)[0][1]
        } if hour_counts else None

        quietest_hour = {
            "hour": hour_counts.most_common()[-1][0],
            "count": hour_counts.most_common()[-1][1]
        } if hour_counts else None

        return {
            "unique_alarm_types": unique_alarms,
            "total_alarms": total_alarms,
            "ignored_messages": len(ignored_messages) if ignored_messages else 0,
            "most_frequent_alarm": most_frequent_alarm,
            "least_frequent_alarm": least_frequent_alarm,
            "average_alarms_per_type": round(avg_alarms_per_type, 2),
            "peak_hour": peak_hour,
            "quietest_hour": quietest_hour
        }

    def _generate_alarm_statistics(self, alarm_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate detailed alarm statistics section."""
        if not alarm_stats:
            return []

        statistics = []
        sorted_alarms = sorted(alarm_stats.items(), key=lambda x: len(x[1]), reverse=True)

        for alarm_name, alarm_entries in sorted_alarms:
            count = len(alarm_entries)
            timestamps = [alarm['timestamp'] for alarm in alarm_entries if alarm.get('timestamp')]
            alarm_ids = [alarm['id'] for alarm in alarm_entries if alarm.get('id')]

            # Calculate timing statistics
            first_occurrence = min(timestamps) if timestamps else None
            last_occurrence = max(timestamps) if timestamps else None

            # Calculate duration span in hours
            duration_hours = None
            if first_occurrence and last_occurrence:
                duration_seconds = (last_occurrence - first_occurrence).total_seconds()
                duration_hours = round(duration_seconds / 3600, 2) if duration_seconds > 0 else 0

            # Hourly distribution for this alarm
            hours = [ts.hour for ts in timestamps if ts]
            hour_counts = Counter(hours)
            most_active_hour = hour_counts.most_common(1)[0][0] if hour_counts else None

            # Create hourly distribution array
            hourly_distribution = []
            for hour in range(24):
                count_hour = hour_counts.get(hour, 0)
                hourly_distribution.append({
                    "hour": hour,
                    "count": count_hour,
                    "time_range": f"{hour:02d}:00-{(hour+1)%24:02d}:00"
                })

            # Recent occurrences (last 5)
            recent_occurrences = []
            for alarm in alarm_entries[:5]:  # Last 5 occurrences
                recent_occurrences.append({
                    "id": alarm.get('id'),
                    "timestamp": alarm.get('timestamp'),
                    "formatted_time": alarm['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if alarm.get('timestamp') else None
                })

            alarm_stat = {
                "alarm_name": alarm_name,
                "total_count": count,
                "first_occurrence": first_occurrence,
                "last_occurrence": last_occurrence,
                "duration_hours": duration_hours,
                "most_active_hour": most_active_hour,
                "hourly_distribution": hourly_distribution,
                "recent_occurrences": recent_occurrences,
                "all_alarm_ids": alarm_ids,
                "frequency_rank": len(statistics) + 1  # Rank by frequency
            }

            statistics.append(alarm_stat)

        return statistics

    def _generate_hourly_analysis(self, alarm_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive hourly analysis."""
        if not alarm_stats:
            return {"total_by_hour": [], "peak_periods": [], "quiet_periods": []}

        # Collect all timestamps
        all_timestamps = []
        for alarm_entries in alarm_stats.values():
            all_timestamps.extend([alarm['timestamp'] for alarm in alarm_entries if alarm.get('timestamp')])

        hours = [ts.hour for ts in all_timestamps if ts]
        hour_counts = Counter(hours)

        # Total by hour
        total_by_hour = []
        for hour in range(24):
            count = hour_counts.get(hour, 0)
            total_by_hour.append({
                "hour": hour,
                "count": count,
                "time_range": f"{hour:02d}:00-{(hour+1)%24:02d}:00",
                "percentage": round((count / len(all_timestamps)) * 100, 2) if all_timestamps else 0
            })

        # Find peak periods (above average)
        average_count = len(all_timestamps) / 24 if all_timestamps else 0
        peak_periods = [
            hour_data for hour_data in total_by_hour
            if hour_data["count"] > average_count and hour_data["count"] > 0
        ]

        # Find quiet periods (below average or zero)
        quiet_periods = [
            hour_data for hour_data in total_by_hour
            if hour_data["count"] <= average_count
        ]

        return {
            "total_by_hour": total_by_hour,
            "peak_periods": sorted(peak_periods, key=lambda x: x["count"], reverse=True),
            "quiet_periods": sorted(quiet_periods, key=lambda x: x["count"]),
            "average_per_hour": round(average_count, 2)
        }

    def _generate_ignored_messages_data(self, ignored_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate ignored messages section."""
        if not ignored_messages:
            return []

        ignored_data = []
        for ignored in ignored_messages:
            # Categorize message type
            message_type = "unknown"
            if ignored.get('file_name'):
                message_type = "file_attachment"
            elif ignored.get('text'):
                message_type = "text_message"
            elif ignored.get('title'):
                message_type = "titled_message"

            ignored_item = {
                "timestamp": ignored.get('timestamp'),
                "reason": ignored.get('reason', 'No reason provided'),
                "message_type": message_type,
                "content": {
                    "text": ignored.get('text'),
                    "title": ignored.get('title'),
                    "fallback": ignored.get('fallback'),
                    "file_name": ignored.get('file_name'),
                    "file_text": ignored.get('file_text')
                },
                "content_length": {
                    "text": len(ignored.get('text', '')),
                    "file_text": len(ignored.get('file_text', ''))
                }
            }

            ignored_data.append(ignored_item)

        return ignored_data

    def _generate_raw_data(
        self,
        alarm_stats: Dict[str, Any],
        ignored_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate raw data section for programmatic access."""
        return {
            "alarm_entries": alarm_stats,
            "ignored_entries": ignored_messages,
            "data_note": "This section contains the original data structures for programmatic access"
        }

    def _get_json_filepath(self, analyzer_params: AnalyzerParams) -> str:
        """Generate the JSON file path."""
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        filename = f"alarm_report_{analyzer_params.product}_{analyzer_params.environment}_{analyzer_params.date_str}.json"
        return os.path.join(reports_dir, filename)

    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")