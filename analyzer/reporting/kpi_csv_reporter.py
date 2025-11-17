"""
KPI CSV Report Generator for QAOps Slack Alarm Analyzer.
"""
import os
import csv
from typing import Dict, Any, List


class KpiCsvReporter:
    """CSV reporter for KPI data."""

    def __init__(self):
        """Initialize KPI CSV reporter."""
        pass

    def generate_report(
        self,
        kpi_data: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]],
        dates: List[str],
        date_range_str: str
    ) -> str:
        """
        Generate KPI CSV report.

        Args:
            kpi_data: Dict structure: {product: {environment: {date: {kpis}}}}
            dates: List of dates in DD-MM-YY format
            date_range_str: Original date range string

        Returns:
            str: Path to the generated CSV file
        """
        csv_path = self._get_csv_filepath(date_range_str)

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Define CSV structure: Product,Environment,Date,Metric,Value
            fieldnames = ['product', 'environment', 'date', 'metric', 'value']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Write data
            for product in sorted(kpi_data.keys()):
                for environment in sorted(kpi_data[product].keys()):
                    for date in dates:
                        kpis = kpi_data[product][environment].get(date)

                        if kpis is None:
                            # Error fetching data for this date
                            writer.writerow({
                                'product': product,
                                'environment': environment,
                                'date': date,
                                'metric': 'ERROR',
                                'value': 'Data collection failed'
                            })
                            continue

                        # Write each metric as a separate row
                        metrics = [
                            ('total_alarms', kpis['total_alarms']),
                            ('analyzable_alarms', kpis['analyzable_alarms']),
                            ('ignored_alarms', kpis['ignored_alarms'])
                        ]

                        # Add oncall metrics only for prod
                        if environment == 'prod':
                            metrics.extend([
                                ('oncall_total', kpis.get('oncall_total', 0)),
                                ('oncall_in_reperibilita', kpis.get('oncall_in_reperibilita', 0))
                            ])

                        for metric_name, metric_value in metrics:
                            writer.writerow({
                                'product': product,
                                'environment': environment,
                                'date': date,
                                'metric': metric_name,
                                'value': metric_value if metric_value is not None else 0
                            })

        return csv_path

    def _get_csv_filepath(self, date_range_str: str) -> str:
        """Generate the CSV file path."""
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        # Sanitize date range for filename
        safe_date_range = date_range_str.replace(':', '_')
        filename = f"kpi_report_{safe_date_range}.csv"
        return os.path.join(reports_dir, filename)
