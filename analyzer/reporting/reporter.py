"""
Protocol definition for report generators.
"""
from typing import Protocol, Dict, Any, List
from ..analyzer_params import AnalyzerParams


class Reporter(Protocol):
    """Protocol for report generators that can create reports in different formats."""

    def generate_report(
        self,
        alarm_stats: Dict[str, Any],
        total_alarms: int,
        analyzer_params: AnalyzerParams,
        ignored_messages: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a report in a specific format.

        Args:
            alarm_stats: Dictionary containing alarm statistics
            total_alarms: Total number of alarm messages
            analyzer_params: Analysis parameters containing configuration
            ignored_messages: List of messages that were ignored

        Returns:
            str: Path to the generated report file
        """
        ...