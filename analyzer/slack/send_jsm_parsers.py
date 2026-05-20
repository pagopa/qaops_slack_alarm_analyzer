"""
SEND product Slack message parsers for messages sent by Jira Service Management
ChatOps (JSM).

JSM messages are rendered as Slack Block Kit cards. The alarm title mirrors the
legacy Opsgenie format and looks like:

    Alert #112717: ALARM: "pn-delivery-B2B-ApiGwAlarm" in EU (Milan)

The title is typically a markdown link inside ``attachments[0].blocks`` (a
section block with ``text.text``). We also support top-level ``message.blocks``
and the legacy attachment ``title``/``text``/``fallback`` fields as a
fallback, to stay resilient to small layout changes by JSM.
"""
import re
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, TYPE_CHECKING

from .base_slack_parser import BaseSlackMessageParser
from .product_environment import ProductEnvironment

if TYPE_CHECKING:
    from ..config.oncall_config import OnCallConfiguration


# `#112717: ALARM: "alarm-name" in EU (Milan)` — the stop-clause guards against
# cases where the title line accidentally gets concatenated with the next
# Status/Responders/Priority/Description label.
JSM_TITLE_PATTERN = re.compile(
    r'#(\d+):\s*ALARM:\s*"([^"]+)"\s+in\s+'
    r'(.+?)(?:\s+(?:Status|Responders|Priority|Description)\b|$)'
)
# Closure messages contain this phrase as a separate Slack post from JSM.
JSM_CLOSED_MARKER = 'CloudWatch closed the alert'

_ALARM_LINE_RE = re.compile(r'\bALARM:\s*"')
_SLACK_LINK_RE = re.compile(r'<[^|>\s]+\|([^>]+)>')
_BOLD_RE = re.compile(r'\*([^*\n]+)\*')
_CODE_RE = re.compile(r'`([^`\n]+)`')


def _parse_slack_ts(ts_str: str) -> datetime:
    return datetime.fromtimestamp(float(ts_str))


def _normalize_slack_text(text: str) -> str:
    text = _SLACK_LINK_RE.sub(r'\1', text)
    text = _BOLD_RE.sub(r'\1', text)
    text = _CODE_RE.sub(r'\1', text)
    text = (
        text.replace('&quot;', '"')
        .replace('&lt;', '<')
        .replace('&gt;', '>')
        .replace('&amp;', '&')
    )
    return text.strip()


def _push(texts: List[str], value: Any) -> None:
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            texts.append(trimmed)


def _collect_elements_text(elements: Optional[Iterable[Any]], texts: List[str]) -> None:
    if not elements:
        return
    for element in elements:
        if not isinstance(element, dict):
            continue
        text = element.get('text')
        if isinstance(text, str):
            _push(texts, text)
        elif isinstance(text, dict):
            _push(texts, text.get('text'))
        nested = element.get('elements')
        if isinstance(nested, list):
            _collect_elements_text(nested, texts)


def _collect_blocks_text(blocks: Optional[Iterable[Any]], texts: List[str]) -> None:
    if not blocks:
        return
    for block in blocks:
        if not isinstance(block, dict):
            continue
        text = block.get('text')
        if isinstance(text, dict):
            _push(texts, text.get('text'))
        for field in block.get('fields', []) or []:
            if isinstance(field, dict):
                _push(texts, field.get('text'))
        _collect_elements_text(block.get('elements'), texts)


def collect_message_texts(message: Dict[str, Any]) -> List[str]:
    """Collect every piece of textual content from a Slack message."""
    texts: List[str] = []
    _push(texts, message.get('text'))
    for attachment in message.get('attachments', []) or []:
        if not isinstance(attachment, dict):
            continue
        _push(texts, attachment.get('title'))
        _push(texts, attachment.get('pretext'))
        _push(texts, attachment.get('text'))
        _push(texts, attachment.get('fallback'))
        _collect_blocks_text(attachment.get('blocks'), texts)
    _collect_blocks_text(message.get('blocks'), texts)
    return texts


def _collect_source_texts(message: Dict[str, Any]) -> List[str]:
    """Collect bot/source identifiers used to detect JSM ChatOps messages."""
    texts: List[str] = []
    _push(texts, message.get('username'))
    bot_profile = message.get('bot_profile')
    if isinstance(bot_profile, dict):
        _push(texts, bot_profile.get('name'))
        _push(texts, bot_profile.get('app_name'))
        _push(texts, bot_profile.get('real_name'))
    for attachment in message.get('attachments', []) or []:
        if not isinstance(attachment, dict):
            continue
        _push(texts, attachment.get('author_name'))
        _push(texts, attachment.get('footer'))
        _push(texts, attachment.get('service_name'))
        _push(texts, attachment.get('text'))
        _push(texts, attachment.get('fallback'))
        _collect_blocks_text(attachment.get('blocks'), texts)
    _collect_blocks_text(message.get('blocks'), texts)
    return texts


def is_jsm_source(message: Dict[str, Any]) -> bool:
    sources = [s.lower() for s in _collect_source_texts(message)]
    if any('opsgenie' in s for s in sources):
        return False
    return any(
        'jira service management' in s or 'jsm chatops' in s
        for s in sources
    )


def find_alarm_title(texts: List[str]) -> Optional[str]:
    for text in texts:
        normalized = _normalize_slack_text(text)
        for line in re.split(r'\n+', normalized):
            candidate = line.strip()
            if _ALARM_LINE_RE.search(candidate):
                return candidate
    return None


def _extract_jsm_alarm_info(
    message: Dict[str, Any],
    is_oncall_fn: Callable[[str], bool],
) -> Optional[Dict[str, Any]]:
    if not is_jsm_source(message):
        return None

    texts = collect_message_texts(message)
    title_line = find_alarm_title(texts)
    if not title_line:
        return None

    # JSM posts a separate Slack message when CloudWatch closes the alert. It
    # carries the same ALARM title — skip it so it isn't counted as an opening.
    if any(JSM_CLOSED_MARKER in _normalize_slack_text(t) for t in texts):
        return None

    match = JSM_TITLE_PATTERN.search(title_line)
    if not match:
        return None

    alarm_id = match.group(1)
    alarm_name = match.group(2).strip()
    location = match.group(3).strip()

    ts = message.get('ts')
    timestamp = _parse_slack_ts(ts) if ts else None

    full_text = '\n'.join(_normalize_slack_text(t) for t in texts)

    return {
        'id': alarm_id,
        'name': alarm_name,
        'location': location,
        'timestamp': timestamp,
        'full_text': full_text,
        'is_oncall': is_oncall_fn(alarm_name),
    }


class SendProdJsmParser(BaseSlackMessageParser):
    """Parser for SEND production messages sent by Jira Service Management ChatOps."""

    def __init__(self, oncall_config: Optional['OnCallConfiguration'] = None):
        super().__init__(ProductEnvironment("SEND", "prod"), oncall_config)

    def extract_alarm_info(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return _extract_jsm_alarm_info(message, self.is_oncall_alarm)


class SendUatJsmParser(BaseSlackMessageParser):
    """Parser for SEND UAT messages sent by Jira Service Management ChatOps."""

    def __init__(self, oncall_config: Optional['OnCallConfiguration'] = None):
        super().__init__(ProductEnvironment("SEND", "uat"), oncall_config)

    def extract_alarm_info(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return _extract_jsm_alarm_info(message, self.is_oncall_alarm)
