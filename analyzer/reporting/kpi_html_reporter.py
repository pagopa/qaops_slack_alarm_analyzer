"""
KPI HTML Report Generator for QAOps Slack Alarm Analyzer.
"""
import os
import json
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

        # Prepare chart data for multi-day reports (2+ days)
        chart_data = {}
        if len(dates) >= 2:
            for product in kpi_data.keys():
                chart_data[product] = {}
                for environment in kpi_data[product].keys():
                    # Extract data for charts
                    total_alarms = []
                    analyzable_alarms = []
                    ignored_alarms = []
                    oncall_total = []
                    oncall_in_reperibilita = []

                    for date in dates:
                        data = kpi_data[product][environment].get(date)
                        if data:
                            total_alarms.append(data.get('total_alarms', 0))
                            analyzable_alarms.append(data.get('analyzable_alarms', 0))
                            ignored_alarms.append(data.get('ignored_alarms', 0))
                            if environment == 'prod':
                                oncall_total.append(data.get('oncall_total', 0) or 0)
                                oncall_in_reperibilita.append(data.get('oncall_in_reperibilita', 0) or 0)
                        else:
                            total_alarms.append(0)
                            analyzable_alarms.append(0)
                            ignored_alarms.append(0)
                            if environment == 'prod':
                                oncall_total.append(0)
                                oncall_in_reperibilita.append(0)

                    chart_data[product][environment] = {
                        'total_alarms': total_alarms,
                        'analyzable_alarms': analyzable_alarms,
                        'ignored_alarms': ignored_alarms,
                        'oncall_total': oncall_total if environment == 'prod' else None,
                        'oncall_in_reperibilita': oncall_in_reperibilita if environment == 'prod' else None
                    }

        # Render template (maintain config order, not alphabetical)
        products = list(kpi_data.keys())
        html_content = template.render(
            kpi_data=kpi_data,
            dates=dates,
            date_range_str=date_range_str,
            products=products,
            chart_data_json=json.dumps(chart_data),
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
