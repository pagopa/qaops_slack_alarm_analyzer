"""
Alarm Type definition for different categories of alarms.

Defines alarm types with their specific rules for time windows,
naming patterns, and channels.
"""
import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class AlarmType:
    """
    Represents a specific type of alarm with its characteristics.

    Attributes:
        product: Product name (SEND, INTEROP)
        environment: Environment (prod, uat, test)
        category: Alarm category ('normal' or 'oncall')
        channel_id: Slack channel ID for this alarm type
        pattern: Regex pattern to match alarm names
        description: Human-readable description
    """
    product: str
    environment: str
    category: str  # 'normal' or 'oncall'
    channel_id: str
    pattern: str
    description: str

    def __post_init__(self):
        """Compile the regex pattern."""
        self._compiled_pattern = re.compile(self.pattern, re.IGNORECASE) if self.pattern else None

    def matches_alarm_name(self, alarm_name: str) -> bool:
        """
        Check if an alarm name matches this alarm type's pattern.

        Args:
            alarm_name: The alarm name to check

        Returns:
            bool: True if the alarm matches this type
        """
        if not alarm_name or not self._compiled_pattern:
            return False
        return bool(self._compiled_pattern.search(alarm_name))

    def is_oncall(self) -> bool:
        """Check if this is an oncall alarm type."""
        return self.category == 'oncall'

    def is_normal(self) -> bool:
        """Check if this is a normal alarm type."""
        return self.category == 'normal'

    def get_time_window(self, date_str: str) -> tuple[float, float]:
        """
        Get the appropriate time window for this alarm type.

        Args:
            date_str: Date string in DD-MM-YY format

        Returns:
            tuple[float, float]: (start_timestamp, end_timestamp) in UTC
        """
        from analyzer.utils.time_utils import get_evening_window, get_oncall_window

        if self.is_oncall():
            return get_oncall_window(date_str)
        else:
            return get_evening_window(date_str)

    def __str__(self):
        return f"AlarmType({self.product}/{self.environment}/{self.category})"

    def __repr__(self):
        return self.__str__()


def build_alarm_types(
    product_config,
    product_name: str,
    environment: str
) -> list[AlarmType]:
    """
    Build list of AlarmType instances for a product and environment.

    Args:
        product_config: Product configuration object
        product_name: Product name (SEND, INTEROP)
        environment: Environment name (prod, uat, test)

    Returns:
        List of AlarmType instances (1 for non-prod, 2 for prod with oncall)
    """
    alarm_types = []

    # Get channel ID for this environment
    channel_id = product_config.get_slack_channel_id(environment)
    if not channel_id:
        return alarm_types

    # Normal alarms always exist
    # Pattern: Exclude oncall alarms (negative lookahead)
    if product_config.oncall_config:
        # Build negative pattern to exclude oncall
        oncall_pattern = product_config.oncall_config.pattern
        # Normal alarm pattern: NOT starting with oncall prefix
        normal_pattern = f"^(?!{oncall_pattern})"
    else:
        # No oncall config, all alarms are normal
        normal_pattern = ".*"

    normal_alarm = AlarmType(
        product=product_name,
        environment=environment,
        category='normal',
        channel_id=channel_id,
        pattern=normal_pattern,
        description=f"{product_name} {environment} normal alarms"
    )
    alarm_types.append(normal_alarm)

    # OnCall alarms only exist for prod environment
    if environment == 'prod' and product_config.oncall_config:
        oncall_channel_id = product_config.oncall_config.channel_id
        oncall_pattern = product_config.oncall_config.pattern

        oncall_alarm = AlarmType(
            product=product_name,
            environment=environment,
            category='oncall',
            channel_id=oncall_channel_id,
            pattern=oncall_pattern,
            description=f"{product_name} {environment} oncall alarms"
        )
        alarm_types.append(oncall_alarm)

    return alarm_types
