"""
PDF report generator for QAOps Slack Alarm Analyzer.
"""
import os
import tempfile
from typing import Dict, Any, List
from ..analyzer_params import AnalyzerParams
from .reporter import Reporter
from .html_reporter import generate_html_report


class PdfReporter:
    """PDF report generator that converts HTML reports to PDF format."""

    def __init__(self):
        """Initialize PDF reporter and check for dependencies."""
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if required PDF generation dependencies are available."""
        try:
            import weasyprint
            self._pdf_engine = 'weasyprint'
            return
        except (ImportError, OSError) as e:
            # WeasyPrint may fail with OSError due to missing system libraries
            pass

        try:
            import pdfkit
            # Check if wkhtmltopdf binary is available
            from pdfkit.configuration import Configuration
            try:
                config = Configuration()
                if not config.wkhtmltopdf:
                    raise ImportError(
                        "pdfkit is installed but wkhtmltopdf binary not found. "
                        "Install wkhtmltopdf: https://wkhtmltopdf.org/downloads.html"
                    )
                self._pdf_engine = 'pdfkit'
                return
            except (OSError, IOError):
                raise ImportError(
                    "pdfkit is installed but wkhtmltopdf binary not found. "
                    "Install wkhtmltopdf: https://wkhtmltopdf.org/downloads.html"
                )
        except ImportError:
            pass

        raise ImportError(
            "PDF generation requires either 'weasyprint' or 'pdfkit' with wkhtmltopdf binary. "
            "Install with: pip install weasyprint OR (pip install pdfkit + wkhtmltopdf binary)"
        )

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
            # Generate PDF from HTML
            pdf_path = self._get_pdf_filepath(analyzer_params)
            self._convert_html_to_pdf(temp_html_path, pdf_path)
            return pdf_path
        except Exception as e:
            # Re-raise with more context
            raise RuntimeError(f"PDF generation failed: {str(e)}") from e
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
        """Generate HTML content for PDF conversion."""
        from .html_reporter import (
            generate_alarm_statistics_html,
            generate_ignored_alarms_html
        )

        # Generate the same HTML content as the HTML reporter but return as string
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alarm Report - {analyzer_params.date_str} - {analyzer_params.product} - {analyzer_params.environment_upper}</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
        }}

        body {{
            font-family: Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.3;
            margin: 0;
            padding: 0;
            background-color: white;
            color: #333;
        }}

        .container {{
            width: 100%;
            max-width: none;
            margin: 0;
            padding: 0;
            background-color: white;
        }}

        h1 {{
            color: #333;
            font-size: 16pt;
            margin: 0 0 15pt 0;
            border-bottom: 2pt solid #d73527;
            padding-bottom: 5pt;
            page-break-after: avoid;
        }}

        h2 {{
            color: #444;
            font-size: 14pt;
            margin: 15pt 0 8pt 0;
            page-break-after: avoid;
            page-break-before: auto;
        }}

        .summary {{
            background-color: #f8f8f8;
            padding: 10pt;
            margin: 8pt 0 12pt 0;
            border-left: 3pt solid #007acc;
            page-break-inside: avoid;
            page-break-after: avoid;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15pt 0;
            font-size: 9pt;
            page-break-inside: auto;
        }}

        th, td {{
            text-align: left;
            padding: 6pt 4pt;
            border: 0.5pt solid #ddd;
            vertical-align: top;
            word-wrap: break-word;
        }}

        th {{
            background-color: #f0f0f0;
            font-weight: bold;
            font-size: 9pt;
        }}

        thead {{
            display: table-header-group;
        }}

        tbody {{
            display: table-row-group;
        }}

        tr {{
            page-break-inside: avoid;
        }}

        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}

        /* Specific column widths for alarm table */
        th:nth-child(1), td:nth-child(1) {{ width: 40%; }}  /* Alarm Name */
        th:nth-child(2), td:nth-child(2) {{ width: 8%; text-align: center; }}   /* Count */
        th:nth-child(3), td:nth-child(3) {{ width: 30%; }}  /* Recent Occurrences */
        th:nth-child(4), td:nth-child(4) {{ width: 22%; }}  /* Hourly Distribution */

        .count-cell {{
            text-align: center;
            font-size: 12pt;
            font-weight: bold;
            color: #d73527;
        }}

        .alarm-name {{
            font-weight: bold;
            color: #333;
            word-break: break-word;
        }}

        .occurrences {{
            font-family: 'Courier New', monospace;
            font-size: 8pt;
            line-height: 1.2;
        }}

        .no-data {{
            text-align: center;
            color: #666;
            font-style: italic;
            padding: 20pt;
        }}

        /* Ensure long text breaks properly */
        td {{
            word-break: break-word;
            overflow-wrap: break-word;
            hyphens: auto;
        }}

        /* Hourly distribution styling */
        .hourly-dist {{
            font-size: 8pt;
            line-height: 1.1;
        }}

        /* Grouping for better page flow */
        .summary + h2 {{
            page-break-before: avoid;
            margin-top: 8pt;
        }}

        h2 + table {{
            page-break-before: avoid;
            margin-top: 8pt;
        }}

        /* Prevent orphaned headers */
        h2:has(+ table) {{
            break-after: avoid-page;
        }}

        /* Print-specific rules */
        @media print {{
            body {{ -webkit-print-color-adjust: exact; }}
            .container {{ page-break-inside: avoid; }}

            /* Ensure continuous flow from summary to table */
            .summary, h2, table {{
                orphans: 2;
                widows: 2;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚨 Alarm Report - {analyzer_params.date_str} - {analyzer_params.product} - {analyzer_params.environment_upper}</h1>

        <div class="summary">
            <strong>Summary:</strong> """

        if total_alarms == 0:
            html_content += f"No alarm messages found for {analyzer_params.date_str}"
        else:
            html_content += f"Found <strong>{total_alarms}</strong> alarm messages"
            if ignored_messages:
                html_content += f" and ignored <strong>{len(ignored_messages)}</strong> messages"

        html_content += """
        </div>
"""

        if total_alarms > 0:
            # Get the HTML but add PDF-specific classes for better formatting
            alarm_html = generate_alarm_statistics_html(alarm_stats, analyzer_params.date_str)
            # Replace generic div elements with hourly-dist class for better PDF formatting
            alarm_html = alarm_html.replace("<div style='font-size: 14px;'>", "<div class='hourly-dist'>")
            html_content += alarm_html
        else:
            html_content += '<p class="no-data">No alarms to display.</p>'

        # Add ignored messages section if provided
        if ignored_messages is not None:
            html_content += generate_ignored_alarms_html(ignored_messages)

        html_content += """
    </div>
</body>
</html>"""

        return html_content

    def _get_pdf_filepath(self, analyzer_params: AnalyzerParams) -> str:
        """Generate the PDF file path."""
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        filename = f"alarm_report_{analyzer_params.product}_{analyzer_params.environment}_{analyzer_params.date_str}.pdf"
        return os.path.join(reports_dir, filename)

    def _convert_html_to_pdf(self, html_path: str, pdf_path: str) -> None:
        """Convert HTML file to PDF using available PDF engine."""
        if self._pdf_engine == 'weasyprint':
            self._convert_with_weasyprint(html_path, pdf_path)
        elif self._pdf_engine == 'pdfkit':
            self._convert_with_pdfkit(html_path, pdf_path)
        else:
            raise RuntimeError("No PDF engine available")

    def _convert_with_weasyprint(self, html_path: str, pdf_path: str) -> None:
        """Convert HTML to PDF using WeasyPrint."""
        import weasyprint
        weasyprint.HTML(filename=html_path).write_pdf(pdf_path)

    def _convert_with_pdfkit(self, html_path: str, pdf_path: str) -> None:
        """Convert HTML to PDF using pdfkit (wkhtmltopdf wrapper)."""
        import pdfkit
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None
        }
        pdfkit.from_file(html_path, pdf_path, options=options)