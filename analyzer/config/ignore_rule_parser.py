"""
Ignore list configuration for filtering out unwanted alarm messages.
"""
import re
from typing import List, Dict, Any, Tuple

from .ignore_rule import IgnoreRule
from typing import List

# Regex pattern for extracting alarm name from SEND alarm titles
# Format: "#45533: ALARM: \"AlarmName\" in Location"
SEND_ALARM_PATTERN = re.compile(r'#\d+: ALARM: "([^"]+)" in .+')


class IgnoreRuleParser:
    """Parser class for evaluating message ignore rules with field paths."""

    def __init__(self, ignore_rules: List[IgnoreRule] = None):
        """
        Initialize the parser with ignore rules.

        Args:
            ignore_rules: List of IgnoreRule objects. If None, uses default rules.
        """
        if ignore_rules is not None:
            self.ignore_rules = ignore_rules
        else:
            # Default fallback rules (backward compatibility)
            self.ignore_rules = [
                IgnoreRule("AWS Notification Message", "files.name"),
            ]

    def should_ignore_message(self, message: Dict[str, Any], environment: str = None) -> bool:
        """
        Check if a message should be ignored based on the ignore rules.

        Args:
            message: Slack message dictionary
            environment: Environment name to check environment-specific rules

        Returns:
            bool: True if message should be ignored, False otherwise
        """
        for rule in self.ignore_rules:
            if self._rule_matches_message(rule, message, environment):
                return True
        return False

    def _rule_matches_message(self, rule: IgnoreRule, message: Dict[str, Any], environment: str = None) -> bool:
        """Check if a specific rule matches the message."""
        # Check if rule applies to this environment
        if environment and not rule.applies_to_environment(environment):
            return False

        # Expand environment placeholders in pattern
        pattern = rule.expand_environment_placeholders(environment) if environment else rule.pattern

        if rule.path == "*":
            # Wildcard: check all fields
            return self._check_all_fields(pattern, message)
        else:
            # Specific path: check only that field
            return self._check_specific_path(pattern, rule.path, message)

    def _check_all_fields(self, pattern: str, message: Dict[str, Any]) -> bool:
        """Check pattern against all message fields."""
        # Check message text
        if self._contains_pattern(pattern, message.get('text', '')):
            return True

        # Check attachments
        attachments = message.get('attachments', [])
        for attachment in attachments:
            for field in ['title', 'fallback', 'text']:
                if self._contains_pattern(pattern, attachment.get(field, '')):
                    return True

        # Check files
        files = message.get('files', [])
        for file_info in files:
            for field in ['name', 'plain_text']:
                if self._contains_pattern(pattern, file_info.get(field, '')):
                    return True

        return False

    def _check_specific_path(self, pattern: str, path: str, message: Dict[str, Any]) -> bool:
        """Check pattern against a specific field path."""
        values = self._extract_values_by_path(path, message)
        for value in values:
            if self._contains_pattern(pattern, value):
                return True
        return False

    def _extract_values_by_path(self, path: str, message: Dict[str, Any]) -> List[str]:
        """Extract values from message based on field path.

        Special paths:
        - attachments.title.alarm_name: Extracts alarm name from SEND alarm title format
        """
        values = []
        path_parts = path.split('.')

        if path == "text":
            values.append(message.get('text', ''))

        elif path_parts[0] == "attachments":
            attachments = message.get('attachments', [])

            # Special handling for alarm_name extraction
            if len(path_parts) == 3 and path_parts[1] == "title" and path_parts[2] == "alarm_name":
                # Extract alarm name from SEND alarm title format
                for attachment in attachments:
                    title = attachment.get('title', '')
                    alarm_name = self._extract_alarm_name_from_title(title)
                    if alarm_name:
                        values.append(alarm_name)

            elif len(path_parts) == 2:
                field = path_parts[1]
                for attachment in attachments:
                    values.append(attachment.get(field, ''))

        elif path_parts[0] == "files":
            files = message.get('files', [])
            if len(path_parts) == 2:
                field = path_parts[1]
                for file_info in files:
                    values.append(file_info.get(field, ''))

        return values

    def _extract_alarm_name_from_title(self, title: str) -> str:
        """Extract alarm name from SEND alarm title format.

        Format: "#45533: ALARM: \"AlarmName\" in Location"
        Returns: "AlarmName" or empty string if not found
        """
        if not title:
            return ""

        match = SEND_ALARM_PATTERN.search(title)
        if match:
            return match.group(1)  # Group 1 is the alarm name
        return ""

    def _contains_pattern(self, pattern: str, text: str) -> bool:
        """Check if text contains the pattern (case-insensitive)."""
        if not text or not pattern:
            return False
        return pattern.lower() in text.lower()

    def get_ignore_reason(self, message: Dict[str, Any]) -> str:
        """Get the reason why a message was ignored."""
        for rule in self.ignore_rules:
            if self._rule_matches_message(rule, message):
                # Use custom reason if provided, otherwise use default pattern-based reason
                if rule.reason:
                    return rule.reason
                elif rule.path == "*":
                    return f"Pattern '{rule.pattern}' found (wildcard search)"
                else:
                    return f"Pattern '{rule.pattern}' found in {rule.path}"
        return "Unknown reason"

    def add_ignore_rule(self, pattern: str, path: str = "*", environments: List[str] = None, reason: str = None) -> None:
        """Add a new ignore rule."""
        if pattern:
            rule = IgnoreRule(pattern, path, environments, reason)
            if rule not in self.ignore_rules:
                self.ignore_rules.append(rule)

    def remove_ignore_rule(self, pattern: str, path: str = "*") -> None:
        """Remove an ignore rule."""
        rule_to_remove = None
        for rule in self.ignore_rules:
            if rule.pattern == pattern and rule.path == path:
                rule_to_remove = rule
                break
        if rule_to_remove:
            self.ignore_rules.remove(rule_to_remove)

    def get_ignore_rules(self) -> List[IgnoreRule]:
        """Get current list of ignore rules."""
        return self.ignore_rules.copy()

    def get_ignore_patterns(self) -> List[str]:
        """Get current list of ignore patterns (for backward compatibility)."""
        return [rule.pattern for rule in self.ignore_rules]