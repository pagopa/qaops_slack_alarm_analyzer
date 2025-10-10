"""
Reporting package for QAOps Slack Alarm Analyzer.

This package contains:
- HTML report generation
- Statistics formatting
- Duration reporting
- File management for reports
- Reporter protocol and implementations
"""

from .html_reporter import (
    generate_html_report,
    generate_duration_report,
    generate_alarm_statistics_html,
    generate_ignored_alarms_html,
    get_report_filepath,
    HtmlReporter
)
from .reporter import Reporter
from .pdf_reporter import PdfReporter
from .csv_reporter import CsvReporter
from .json_reporter import JsonReporter

__all__ = [
    'generate_html_report',
    'generate_duration_report',
    'generate_alarm_statistics_html',
    'generate_ignored_alarms_html',
    'get_report_filepath',
    'HtmlReporter',
    'Reporter',
    'PdfReporter',
    'CsvReporter',
    'JsonReporter'
]