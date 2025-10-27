"""
Duration analysis parameters.

This module contains the DurationParams class that encapsulates all parameters
needed for duration analysis and reporting.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class DurationParams:
    """Parameters for duration analysis and reporting."""

    durations: List[Tuple[str, str, float, float, float]]  # (alarm_id, alarm_name, open_ts, close_ts, duration)
    date_str: str
    days_back: int
    oldest: float
    latest: float
    num_messages: int
    num_openings: int
    num_closings: int

    def __post_init__(self):
        """Validate parameters after initialization."""
        if self.days_back <= 0:
            raise ValueError("days_back must be positive")
        if self.days_back > 30:
            raise ValueError("days_back cannot exceed 30")
        if self.oldest >= self.latest:
            raise ValueError("oldest timestamp must be before latest timestamp")
        if self.num_messages < 0:
            raise ValueError("num_messages cannot be negative")
        if self.num_openings < 0:
            raise ValueError("num_openings cannot be negative")
        if self.num_closings < 0:
            raise ValueError("num_closings cannot be negative")

    @property
    def date_str_safe(self) -> str:
        """Get date string with special characters replaced for safe filename usage.

        Replaces ':' with '_' to ensure compatibility with:
        - Windows filesystems (: is a reserved character)
        - GitHub Actions artifacts (: not allowed in artifact names)
        - Cross-platform file operations

        Examples:
            '2025-10-27' -> '2025-10-27' (no change)
            '24-10-25:27-10-25' -> '24-10-25_27-10-25'
        """
        return self.date_str.replace(':', '_')
