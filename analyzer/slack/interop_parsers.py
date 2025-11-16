"""
INTEROP product Slack message parsers for different environments.
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING

from .base_slack_parser import BaseSlackMessageParser
from .product_environment import ProductEnvironment

if TYPE_CHECKING:
    from ..config.oncall_config import OnCallConfiguration


def parse_slack_ts(ts_str: str) -> datetime:
    """Parse Slack timestamp string to datetime."""
    return datetime.fromtimestamp(float(ts_str))


class InteropProdParser(BaseSlackMessageParser):
    """Parser for INTEROP production environment messages."""

    def __init__(self, oncall_config: Optional['OnCallConfiguration'] = None):
        super().__init__(ProductEnvironment("INTEROP", "prod"), oncall_config)

    def extract_alarm_info(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract alarm info from INTEROP prod Slack message files."""
        files = message.get('files', [])
        if not files:
            return None

        alarm_file = files[0]
        alarm_name_raw = alarm_file.get('name', '')
        alarm_id = alarm_file.get('id', 'N/A')
        full_text = alarm_file.get('plain_text', '')

        # Extract alarm name from quotes: ALARM: "alarm-name" in Location -> alarm-name
        alarm_name_match = re.search(r'"([^"]+)"', alarm_name_raw)
        if alarm_name_match:
            alarm_name = alarm_name_match.group(1)
        else:
            # Fallback to raw name if no quotes found
            alarm_name = alarm_name_raw

        # Extract location from the raw name (after "in ")
        location_match = re.search(r'in\s+(.+)', alarm_name_raw)
        location = location_match.group(1).strip() if location_match else 'Unknown'

        ts = message.get('ts')
        timestamp = parse_slack_ts(ts) if ts else None

        return {
            'id': alarm_id,
            'name': alarm_name,
            'location': location,
            'timestamp': timestamp,
            'full_text': full_text,
            'is_oncall': self.is_oncall_alarm(alarm_name)
        }


class InteropTestParser(BaseSlackMessageParser):
    """Parser for INTEROP test environment messages."""

    def __init__(self, oncall_config: Optional['OnCallConfiguration'] = None):
        super().__init__(ProductEnvironment("INTEROP", "test"), oncall_config)

    def extract_alarm_info(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract alarm info from INTEROP test messages - same logic as prod for now."""
        # For now, test uses the same parsing logic as production
        # This can be customized if test has different message formats
        prod_parser = InteropProdParser(self.oncall_config)
        return prod_parser.extract_alarm_info(message)