"""
Slack integration package for QAOps Slack Alarm Analyzer.

This package provides:
- Slack API integration for fetching messages
- Flexible message parsing system based on product and environment combinations
"""

from .base_slack_parser import BaseSlackMessageParser
from .product_environment import ProductEnvironment
from .parser_provider import SlackMessageParserProvider
from .send_parsers import SendProdParser, SendUatParser
from .interop_parsers import InteropProdParser, InteropTestParser
from .slack_api import SlackAPIError, fetch_slack_messages

__all__ = [
    'BaseSlackMessageParser',
    'ProductEnvironment',
    'SlackMessageParserProvider',
    'SendProdParser',
    'SendUatParser',
    'InteropProdParser',
    'InteropTestParser',
    'SlackAPIError',
    'fetch_slack_messages'
]