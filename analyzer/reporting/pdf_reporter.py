"""
PDF report generator for QAOps Slack Alarm Analyzer.
Uses WeasyPrint for HTML to PDF conversion.
"""
import os
import tempfile
from typing import Dict, Any, List
import weasyprint
from jinja2 import Environment, FileSystemLoader
from collections import Counter
from ..analyzer_params import AnalyzerParams
from .reporter import Reporter


class PdfReporter:
    """PDF report generator that converts HTML reports to PDF format."""

    def __init__(self):
        """Initialize PDF reporter."""
        pass

    def generate_report(
        self,
        alarm_stats: Dict[str, Any],
        total_alarms: int,
        analyzer_params: AnalyzerParams,
        ignored_messages: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a PDF report by converting HTML report to PDF.

        Args:
            alarm_stats: Dictionary containing alarm statistics
            total_alarms: Total number of alarm messages
            analyzer_params: Analysis parameters containing configuration
            ignored_messages: List of messages that were ignored

        Returns:
            str: Path to the generated PDF report file
        """
        # First generate HTML content using existing HTML reporter
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_html:
            html_content = self._generate_html_content(alarm_stats, total_alarms, analyzer_params, ignored_messages)
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
        total_alarms: int,
        analyzer_params: AnalyzerParams,
        ignored_messages: List[Dict[str, Any]]
    ) -> str:
        """Generate HTML content for PDF conversion using Jinja2 template."""
        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))

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

        # Load template
        template = env.get_template('pdf_report.html')

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

        return html_content

    def _get_pdf_filepath(self, analyzer_params: AnalyzerParams) -> str:
        """Generate the PDF file path."""
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        filename = f"alarm_report_{analyzer_params.product}_{analyzer_params.environment}_{analyzer_params.date_str}.pdf"
        return os.path.join(reports_dir, filename)