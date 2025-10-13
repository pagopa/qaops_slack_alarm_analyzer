"""
INTEROP product Slack message parsers for different environments.
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional

from .base_slack_parser import BaseSlackMessageParser
from .product_environment import ProductEnvironment


def parse_slack_ts(ts_str: str) -> datetime:
    """Parse Slack timestamp string to datetime."""
    return datetime.fromtimestamp(float(ts_str))


class InteropProdParser(BaseSlackMessageParser):
    """Parser for INTEROP production environment messages."""

    def __init__(self):
        super().__init__(ProductEnvironment("INTEROP", "prod"))

    def extract_alarm_info(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract alarm info from INTEROP prod Slack message files."""
        files = message.get('files', [])
        if not files:
            return None

        alarm_file = files[0]
        alarm_name = alarm_file.get('name', '')
        alarm_id = alarm_file.get('id', 'N/A')
        full_text = alarm_file.get('plain_text', '')

        location_match = re.search(r'in\s+(.+)', alarm_name)
        location = location_match.group(1).strip() if location_match else 'Unknown'

        ts = message.get('ts')
        timestamp = parse_slack_ts(ts) if ts else None

        return {
            'id': alarm_id,
            'name': alarm_name,
            'location': location,
            'timestamp': timestamp,
            'full_text': full_text
        }


class InteropTestParser(BaseSlackMessageParser):
    """Parser for INTEROP test environment messages."""

    def __init__(self):
        super().__init__(ProductEnvironment("INTEROP", "test"))

    def extract_alarm_info(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract alarm info from INTEROP test messages - same logic as prod for now."""
        # For now, test uses the same parsing logic as production
        # This can be customized if test has different message formats
        prod_parser = InteropProdParser()
        return prod_parser.extract_alarm_info(message)