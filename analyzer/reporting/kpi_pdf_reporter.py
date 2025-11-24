"""
KPI PDF Report Generator for QAOps Slack Alarm Analyzer.
"""
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, List
import weasyprint
from jinja2 import Environment, FileSystemLoader, select_autoescape


class KpiPdfReporter:
    """PDF reporter for KPI dashboard."""

    def __init__(self):
        """Initialize KPI PDF reporter."""
        pass

    def generate_report(
        self,
        kpi_data: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]],
        dates: List[str],
        date_range_str: str
    ) -> str:
        """
        Generate KPI PDF report.

        Args:
            kpi_data: Dict structure: {product: {environment: {date: {kpis}}}}
            dates: List of dates in DD-MM-YY format
            date_range_str: Original date range string

        Returns:
            str: Path to the generated PDF file
        """
        # Generate HTML content
        html_content = self._generate_html_content(kpi_data, dates, date_range_str)

        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_html:
            temp_html.write(html_content)
            temp_html_path = temp_html.name

        try:
            # Generate PDF from HTML (maintain config order, not alphabetical)
            products = list(kpi_data.keys())
            pdf_path = self._get_pdf_filepath(date_range_str, products)
            weasyprint.HTML(filename=temp_html_path).write_pdf(pdf_path)
            return pdf_path
        finally:
            # Clean up temporary HTML file
            if os.path.exists(temp_html_path):
                os.unlink(temp_html_path)

    def _generate_html_content(
        self,
        kpi_data: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]],
        dates: List[str],
        date_range_str: str
    ) -> str:
        """Generate HTML content for PDF conversion."""
        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Load PDF template (we'll use the same as HTML for now)
        template = env.get_template('kpi_report_pdf.html')

        # Render template (maintain config order, not alphabetical)
        html_content = template.render(
            kpi_data=kpi_data,
            dates=dates,
            date_range_str=date_range_str,
            products=list(kpi_data.keys()),
            now=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

        return html_content

    def _get_pdf_filepath(self, date_range_str: str, products: List[str]) -> str:
        """Generate the PDF file path with product names if specified."""
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        # Sanitize date range for filename
        safe_date_range = date_range_str.replace(':', '_')

        # Include product names in filename if not all products
        if products:
            products_str = '_'.join(products)
            filename = f"kpi_report_{products_str}_{safe_date_range}.pdf"
        else:
            filename = f"kpi_report_{safe_date_range}.pdf"

        return os.path.join(reports_dir, filename)
