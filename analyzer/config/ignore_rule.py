"""
Ignore rule definition for filtering alarm messages.
"""
from typing import List, Optional


class IgnoreRule:
    """Represents a single ignore rule with pattern, field path, environment restrictions, and reason."""

    def __init__(self, pattern: str, path: str = "*", environments: List[str] = None, reason: Optional[str] = None):
        self.pattern = pattern
        self.path = path
        self.environments = environments or []  # Empty list means applies to all environments
        self.reason = reason  # Optional explanation for why this rule exists

    def applies_to_environment(self, environment: str) -> bool:
        """Check if this rule applies to the given environment."""
        return not self.environments or environment in self.environments

    def expand_environment_placeholders(self, environment: str) -> str:
        """Expand environment placeholders in the pattern."""
        return self.pattern.replace("[#env#]", environment)

    def __str__(self):
        env_str = f", environments={self.environments}" if self.environments else ""
        reason_str = f", reason='{self.reason}'" if self.reason else ""
        return f"IgnoreRule(pattern='{self.pattern}', path='{self.path}'{env_str}{reason_str})"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, IgnoreRule):
            return False
        return (self.pattern == other.pattern and
                self.path == other.path and
                self.environments == other.environments and
                self.reason == other.reason)