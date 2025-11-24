"""
Unified time constraint for ignore rules.
Supports periods, weekdays, and hours in a single structure.
"""
from datetime import datetime, time
from typing import List, Optional, Dict, Any


class DateTimePeriod:
    """Represents a datetime period (from start to end)."""

    def __init__(self, start: Optional[str] = None, end: Optional[str] = None):
        """
        Initialize a datetime period.

        Args:
            start: Start datetime in ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS).
                  If None, valid from the beginning of time.
            end: End datetime in ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS).
                If None, valid until the end of time.
        """
        self.start, self.start_is_date_only = self._parse_datetime(start) if start else (None, False)
        self.end, self.end_is_date_only = self._parse_datetime(end) if end else (None, False)

        # Validate that start is before end if both are provided
        if self.start and self.end and self.start > self.end:
            raise ValueError(f"start ({start}) must be before end ({end})")

    def _parse_datetime(self, dt_str: str) -> tuple:
        """Parse a datetime string in ISO format."""
        formats = [
            ("%Y-%m-%d %H:%M:%S", False),
            ("%Y-%m-%d %H:%M", False),
            ("%Y-%m-%d", True)
        ]

        for fmt, is_date_only in formats:
            try:
                return datetime.strptime(dt_str, fmt), is_date_only
            except ValueError:
                continue

        raise ValueError(f"Invalid datetime format: {dt_str}. Expected YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")

    def contains(self, check_datetime: datetime) -> bool:
        """Check if the given datetime falls within this period."""
        # Check start
        if self.start:
            if self.start_is_date_only:
                if check_datetime.date() < self.start.date():
                    return False
            else:
                if check_datetime < self.start:
                    return False

        # Check end
        if self.end:
            if self.end_is_date_only:
                if check_datetime.date() > self.end.date():
                    return False
            else:
                if check_datetime > self.end:
                    return False

        return True

    def __str__(self):
        start_str = self.start.strftime("%Y-%m-%d %H:%M:%S") if self.start else "∞"
        end_str = self.end.strftime("%Y-%m-%d %H:%M:%S") if self.end else "∞"
        return f"{start_str} → {end_str}"

    def __repr__(self):
        return f"DateTimePeriod({self})"

    def __eq__(self, other):
        if not isinstance(other, DateTimePeriod):
            return False
        return self.start == other.start and self.end == other.end


class TimeRange:
    """Represents a time range within a day (e.g., 01:00-05:00)."""

    def __init__(self, start: str, end: str):
        """
        Initialize a time range.

        Args:
            start: Start time in HH:MM format (24-hour)
            end: End time in HH:MM format (24-hour)
        """
        self.start = self._parse_time(start)
        self.end = self._parse_time(end)

    def _parse_time(self, time_str: str) -> time:
        """Parse a time string in HH:MM format."""
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM (24-hour format)")

    def contains(self, check_time: time) -> bool:
        """Check if the given time falls within this range."""
        # Handle ranges that cross midnight
        if self.start <= self.end:
            # Normal range (e.g., 09:00-17:00)
            return self.start <= check_time <= self.end
        else:
            # Range crossing midnight (e.g., 22:00-02:00)
            return check_time >= self.start or check_time <= self.end

    def __str__(self):
        return f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')}"

    def __repr__(self):
        return f"TimeRange({self})"

    def __eq__(self, other):
        if not isinstance(other, TimeRange):
            return False
        return self.start == other.start and self.end == other.end


class TimeConstraint:
    """
    Unified time constraint that can specify:
    - Periods: datetime ranges (start to end)
    - Weekdays: specific days of the week
    - Hours: specific time ranges within a day
    """

    # Mapping of weekday names to numbers (0=Monday, 6=Sunday)
    WEEKDAY_MAP = {
        "monday": 0, "mon": 0,
        "tuesday": 1, "tue": 1,
        "wednesday": 2, "wed": 2,
        "thursday": 3, "thu": 3,
        "friday": 4, "fri": 4,
        "saturday": 5, "sat": 5,
        "sunday": 6, "sun": 6,
    }

    def __init__(
        self,
        periods: Optional[List[Dict[str, str]]] = None,
        weekdays: Optional[List[Any]] = None,
        hours: Optional[List[Dict[str, str]]] = None
    ):
        """
        Initialize time constraint.

        Args:
            periods: List of datetime periods, e.g., [{"start": "2025-01-01", "end": "2025-01-31"}]
            weekdays: List of weekdays (0-6 or names like "monday", "mon")
            hours: List of time ranges, e.g., [{"start": "01:00", "end": "05:00"}]
        """
        # Parse datetime periods
        self.periods: List[DateTimePeriod] = []
        if periods:
            for period_dict in periods:
                if isinstance(period_dict, dict):
                    start = period_dict.get("start")
                    end = period_dict.get("end")
                    self.periods.append(DateTimePeriod(start=start, end=end))

        # Parse weekdays
        self.weekdays: List[int] = []
        if weekdays:
            for day in weekdays:
                if isinstance(day, int):
                    if 0 <= day <= 6:
                        self.weekdays.append(day)
                    else:
                        raise ValueError(f"Invalid weekday number: {day}. Must be 0-6 (0=Monday, 6=Sunday)")
                elif isinstance(day, str):
                    day_lower = day.lower()
                    if day_lower in self.WEEKDAY_MAP:
                        self.weekdays.append(self.WEEKDAY_MAP[day_lower])
                    else:
                        raise ValueError(f"Invalid weekday name: {day}. Expected: monday, tuesday, etc.")

        # Parse hour ranges
        self.hours: List[TimeRange] = []
        if hours:
            for hour_dict in hours:
                if isinstance(hour_dict, dict) and "start" in hour_dict and "end" in hour_dict:
                    self.hours.append(TimeRange(hour_dict["start"], hour_dict["end"]))

    def is_empty(self) -> bool:
        """Check if this constraint has no restrictions (matches always)."""
        return not self.periods and not self.weekdays and not self.hours

    def matches(self, check_datetime: datetime) -> bool:
        """
        Check if the given datetime matches this constraint.

        If no constraints are configured, returns True (matches always).
        All configured constraints must match for the result to be True (AND logic).
        Within each constraint type, at least one must match (OR logic).

        Args:
            check_datetime: Datetime to check

        Returns:
            bool: True if the datetime matches all configured constraints
        """
        # If no constraints are configured, always match
        if self.is_empty():
            return True

        # Check periods (at least one must match if configured)
        if self.periods:
            period_match = any(period.contains(check_datetime) for period in self.periods)
            if not period_match:
                return False

        # Check weekdays (must match if configured)
        if self.weekdays:
            weekday_match = check_datetime.weekday() in self.weekdays
            if not weekday_match:
                return False

        # Check hours (at least one must match if configured)
        if self.hours:
            hour_match = any(hour_range.contains(check_datetime.time()) for hour_range in self.hours)
            if not hour_match:
                return False

        # All configured constraints matched
        return True

    def __str__(self):
        parts = []
        if self.periods:
            periods_str = ", ".join(str(p) for p in self.periods)
            parts.append(f"periods=[{periods_str}]")
        if self.weekdays:
            weekday_names = [name for name, num in self.WEEKDAY_MAP.items() if num in self.weekdays and len(name) > 3]
            parts.append(f"weekdays={weekday_names}")
        if self.hours:
            hours_str = ", ".join(str(h) for h in self.hours)
            parts.append(f"hours=[{hours_str}]")
        return f"TimeConstraint({', '.join(parts)})" if parts else "TimeConstraint(empty)"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, TimeConstraint):
            return False
        return (self.periods == other.periods and
                self.weekdays == other.weekdays and
                self.hours == other.hours)
