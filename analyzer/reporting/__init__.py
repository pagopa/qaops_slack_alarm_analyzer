"""
Reporting package for QAOps Slack Alarm Analyzer.

This package contains:
- HTML report generation
- Statistics formatting
- Duration reporting
- File management for reports
"""

from .report import (
    generate_html_report,
    generate_duration_report,
    generate_alarm_statistics_html,
    generate_ignored_alarms_html,
    get_report_filepath
)

__all__ = [
    'generate_html_report',
    'generate_duration_report',
    'generate_alarm_statistics_html',
    'generate_ignored_alarms_html',
    'get_report_filepath'
]