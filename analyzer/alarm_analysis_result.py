"""
Alarm Analysis Result model.

Contains the results of alarm analysis including statistics and categorizations.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class AlarmAnalysisResult:
    """
    Results of alarm analysis for a specific time period and alarm type.

    Attributes:
        alarm_stats: Dict mapping alarm name to list of alarm entries
        total_alarms: Total number of alarm messages found
        analyzable_alarms: Number of alarms that can be analyzed (total - ignored)
        ignored_alarms: Number of alarms ignored by rules
        ignored_messages: List of ignored alarm messages with details
        oncall_total: Number of oncall alarms (only for prod environment)
        oncall_in_reperibilita: Number of oncall alarms outside office hours
        alarm_type: The AlarmType this result is for
    """
    alarm_stats: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    total_alarms: int = 0
    analyzable_alarms: int = 0
    ignored_alarms: int = 0
    ignored_messages: List[Dict[str, Any]] = field(default_factory=list)
    oncall_total: int = 0
    oncall_in_reperibilita: int = 0
    alarm_type: Any = None  # AlarmType instance

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'total_alarms': self.total_alarms,
            'analyzable_alarms': self.analyzable_alarms,
            'ignored_alarms': self.ignored_alarms,
            'oncall_total': self.oncall_total,
            'oncall_in_reperibilita': self.oncall_in_reperibilita,
            'alarm_type': str(self.alarm_type) if self.alarm_type else None
        }

    def __str__(self):
        return (f"AlarmAnalysisResult(total={self.total_alarms}, "
                f"analyzable={self.analyzable_alarms}, "
                f"oncall={self.oncall_total})")

    def __repr__(self):
        return self.__str__()


def merge_analysis_results(results: List[AlarmAnalysisResult]) -> AlarmAnalysisResult:
    """
    Merge multiple AlarmAnalysisResult instances into one.

    Used when combining results from different alarm types (normal + oncall).

    Args:
        results: List of AlarmAnalysisResult to merge

    Returns:
        Merged AlarmAnalysisResult
    """
    merged = AlarmAnalysisResult()

    for result in results:
        # Merge alarm stats
        for alarm_name, alarm_entries in result.alarm_stats.items():
            if alarm_name not in merged.alarm_stats:
                merged.alarm_stats[alarm_name] = []
            merged.alarm_stats[alarm_name].extend(alarm_entries)

        # Sum up statistics
        merged.total_alarms += result.total_alarms
        merged.analyzable_alarms += result.analyzable_alarms
        merged.ignored_alarms += result.ignored_alarms
        merged.oncall_total += result.oncall_total
        merged.oncall_in_reperibilita += result.oncall_in_reperibilita

        # Merge ignored messages
        merged.ignored_messages.extend(result.ignored_messages)

    return merged
