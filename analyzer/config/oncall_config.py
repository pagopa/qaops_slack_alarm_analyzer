"""
OnCall configuration for identifying urgent alarms that require immediate attention.
"""
import re
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


# Office hours in Italy (Europe/Rome timezone)
OFFICE_HOURS_START = 9  # 09:00
OFFICE_HOURS_END = 18   # 18:00
ITALY_TIMEZONE = ZoneInfo("Europe/Rome")


def is_oncall_in_reperibilita(alarm_timestamp: datetime) -> bool:
    """
    Check if an oncall alarm occurred outside office hours (in reperibilità).

    Office hours are defined as 9:00-18:00 Italy time (Europe/Rome timezone).
    This automatically handles DST transitions (UTC+1 or UTC+2).

    Args:
        alarm_timestamp: The timestamp of the alarm (can be naive local time or aware UTC)

    Returns:
        bool: True if the alarm occurred outside office hours (in reperibilità)
    """
    if not alarm_timestamp:
        return False

    # Convert alarm timestamp to Italy timezone
    # If the timestamp is naive (no timezone), it's in local time from fromtimestamp()
    # We need to convert it properly to Italy timezone
    if alarm_timestamp.tzinfo is None:
        # Naive datetime from fromtimestamp() is in local timezone
        # Convert to epoch (assumes local time) and then to Italy timezone
        timestamp_epoch = alarm_timestamp.timestamp()
        italy_time = datetime.fromtimestamp(timestamp_epoch, tz=ITALY_TIMEZONE)
    else:
        # Already aware, just convert to Italy timezone
        italy_time = alarm_timestamp.astimezone(ITALY_TIMEZONE)

    hour = italy_time.hour

    # Check if outside office hours (before 9:00 or after 18:00)
    return hour < OFFICE_HOURS_START or hour >= OFFICE_HOURS_END


class OnCallConfiguration:
    """Configuration for identifying and managing oncall alarms."""

    def __init__(self, channel_id: str, pattern: str):
        """
        Initialize oncall configuration.

        Args:
            channel_id: Slack channel ID where oncall alarms are posted
            pattern: Regular expression pattern to identify oncall alarms in the alarm name
        """
        self.channel_id = channel_id
        self.pattern = pattern
        self._compiled_pattern = re.compile(pattern, re.IGNORECASE) if pattern else None

    def is_oncall_alarm(self, alarm_name: str) -> bool:
        """
        Check if an alarm is an oncall alarm based on the configured pattern.

        Args:
            alarm_name: The name of the alarm to check

        Returns:
            bool: True if the alarm name matches the oncall pattern
        """
        if not alarm_name or not self._compiled_pattern:
            return False
        return bool(self._compiled_pattern.search(alarm_name))

    def __str__(self):
        return f"OnCallConfiguration(channel_id='{self.channel_id}', pattern='{self.pattern}')"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, OnCallConfiguration):
            return False
        return self.channel_id == other.channel_id and self.pattern == other.pattern
