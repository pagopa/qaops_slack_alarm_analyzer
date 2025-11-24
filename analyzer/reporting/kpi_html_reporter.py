"""
KPI HTML Report Generator for QAOps Slack Alarm Analyzer.
"""
import os
from datetime import datetime
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader, select_autoescape


class KpiHtmlReporter:
    """HTML reporter for KPI dashboard."""

    def __init__(self):
        """Initialize KPI HTML reporter."""
        pass

    def generate_report(
        self,
        kpi_data: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]],
        dates: List[str],
        date_range_str: str
    ) -> str:
        """
        Generate KPI HTML report.

        Args:
            kpi_data: Dict structure: {product: {environment: {date: {kpis}}}}
            dates: List of dates in DD-MM-YY format
            date_range_str: Original date range string

        Returns:
            str: Path to the generated HTML file
        """
        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Load template
        template = env.get_template('kpi_report.html')

        # Render template (maintain config order, not alphabetical)
        products = list(kpi_data.keys())
        html_content = template.render(
            kpi_data=kpi_data,
            dates=dates,
            date_range_str=date_range_str,
            products=products,
            now=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

        # Save to file
        html_path = self._get_html_filepath(date_range_str, products)
        with open(html_path, 'w', encoding='utf-8') as html_file:
            html_file.write(html_content)

        return html_path

    def _get_html_filepath(self, date_range_str: str, products: List[str]) -> str:
        """Generate the HTML file path with product names if specified."""
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        # Sanitize date range for filename
        safe_date_range = date_range_str.replace(':', '_')

        # Include product names in filename if not all products
        if products:
            products_str = '_'.join(products)
            filename = f"kpi_report_{products_str}_{safe_date_range}.html"
        else:
            filename = f"kpi_report_{safe_date_range}.html"

        return os.path.join(reports_dir, filename)
