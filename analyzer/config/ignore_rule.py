"""
Ignore rule definition for filtering alarm messages.
"""
from datetime import datetime
from typing import List, Optional

from .time_constraint import TimeConstraint


class IgnoreRule:
    """Represents a single ignore rule with pattern, field path, environment restrictions, and reason."""

    def __init__(
        self,
        pattern: str,
        path: str = "*",
        environments: List[str] = None,
        reason: Optional[str] = None,
        validity: Optional[TimeConstraint] = None,
        exclusions: Optional[TimeConstraint] = None
    ):
        """
        Initialize an ignore rule.

        Args:
            pattern: Pattern to match in messages
            path: Field path to check (default: "*" for all fields)
            environments: List of environments where this rule applies (empty = all)
            reason: Optional explanation for why this rule exists
            validity: TimeConstraint defining when the rule is valid (None = always valid)
            exclusions: TimeConstraint defining when the rule is NOT valid (None = no exclusions)
        """
        self.pattern = pattern
        self.path = path
        self.environments = environments or []  # Empty list means applies to all environments
        self.reason = reason  # Optional explanation for why this rule exists
        self.validity = validity  # None or empty means always valid
        self.exclusions = exclusions  # None or empty means no exclusions

    def applies_to_environment(self, environment: str) -> bool:
        """Check if this rule applies to the given environment."""
        return not self.environments or environment in self.environments

    def is_valid_at(self, check_datetime: datetime) -> bool:
        """
        Check if this rule is valid at the given datetime.

        A rule is valid if:
        1. The validity constraint matches (if configured), AND
        2. The exclusions constraint does NOT match (if configured)

        Args:
            check_datetime: Datetime to check

        Returns:
            bool: True if the rule is valid at the given datetime
        """
        # Check validity constraint
        if self.validity and not self.validity.is_empty():
            if not self.validity.matches(check_datetime):
                return False

        # Check exclusions constraint (inverse logic)
        if self.exclusions and not self.exclusions.is_empty():
            if self.exclusions.matches(check_datetime):
                return False  # Excluded, so not valid

        return True

    def expand_environment_placeholders(self, environment: str) -> str:
        """Expand environment placeholders in the pattern."""
        return self.pattern.replace("[#env#]", environment)

    def __str__(self):
        env_str = f", environments={self.environments}" if self.environments else ""
        reason_str = f", reason='{self.reason}'" if self.reason else ""
        validity_str = f", validity={self.validity}" if self.validity and not self.validity.is_empty() else ""
        exclusions_str = f", exclusions={self.exclusions}" if self.exclusions and not self.exclusions.is_empty() else ""
        return f"IgnoreRule(pattern='{self.pattern}', path='{self.path}'{env_str}{reason_str}{validity_str}{exclusions_str})"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, IgnoreRule):
            return False
        return (self.pattern == other.pattern and
                self.path == other.path and
                self.environments == other.environments and
                self.reason == other.reason and
                self.validity == other.validity and
                self.exclusions == other.exclusions)