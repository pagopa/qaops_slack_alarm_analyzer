"""
SEND product Slack message parsers for different environments.
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING

from .base_slack_parser import BaseSlackMessageParser
from .product_environment import ProductEnvironment

if TYPE_CHECKING:
    from ..config.oncall_config import OnCallConfiguration

# Regex patterns for SEND alarms
OPENING_PATTERN = re.compile(r'#(\d+): ALARM: "([^"]+)" in (.+)')
CLOSING_PATTERN = re.compile(r'CloudWatch closed alert .*?\|#(\d+)> "ALARM:\s*"([^"]+)"\s*in\s+([^"]+)"')


def parse_slack_ts(ts_str: str) -> datetime:
    """Parse Slack timestamp string to datetime."""
    return datetime.fromtimestamp(float(ts_str))


class SendProdParser(BaseSlackMessageParser):
    """Parser for SEND production environment messages."""

    def __init__(self, oncall_config: Optional['OnCallConfiguration'] = None):
        super().__init__(ProductEnvironment("SEND", "prod"), oncall_config)

    def extract_alarm_info(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract alarm info from SEND prod Slack message attachments."""
        if not message.get('attachments') or len(message['attachments']) == 0:
            return None

        attachment = message['attachments'][0]
        title = attachment.get('title', '')
        fallback = attachment.get('fallback', '')

        # Pattern for TITLE: "#45533: ALARM: \"AlarmName\" in Location"
        title_pattern = OPENING_PATTERN
        title_match = re.search(title_pattern, title)

        if title_match:
            alarm_id = title_match.group(1)
            alarm_name = title_match.group(2)
            location = title_match.group(3)

            ts = message.get("ts")
            timestamp = parse_slack_ts(ts) if ts else None

            return {
                'id': alarm_id,
                'name': alarm_name,
                'location': location,
                'timestamp': timestamp,
                'full_text': fallback,
                'is_oncall': self.is_oncall_alarm(alarm_name)
            }

        # Fallback: try to extract from fallback text
        fallback_match = re.search(OPENING_PATTERN, fallback)
        if fallback_match:
            alarm_id = fallback_match.group(1)
            alarm_name = fallback_match.group(2)
            location = fallback_match.group(3)

            ts = message.get("ts")
            timestamp = parse_slack_ts(ts) if ts else None

            return {
                'id': alarm_id,
                'name': alarm_name,
                'location': location,
                'timestamp': timestamp,
                'full_text': fallback,
                'is_oncall': self.is_oncall_alarm(alarm_name)
            }

        return None


class SendUatParser(BaseSlackMessageParser):
    """Parser for SEND UAT environment messages."""

    def __init__(self, oncall_config: Optional['OnCallConfiguration'] = None):
        super().__init__(ProductEnvironment("SEND", "uat"), oncall_config)

    def extract_alarm_info(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract alarm info from SEND UAT messages - same logic as prod for now."""
        # For now, UAT uses the same parsing logic as production
        # This can be customized if UAT has different message formats
        prod_parser = SendProdParser(self.oncall_config)
        return prod_parser.extract_alarm_info(message)