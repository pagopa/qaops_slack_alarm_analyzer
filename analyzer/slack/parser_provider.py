"""
Provider for Slack message parsers based on product and environment.
"""
from typing import Dict, Optional, TYPE_CHECKING

from .base_slack_parser import BaseSlackMessageParser
from .product_environment import ProductEnvironment
from .send_parsers import SendProdParser, SendUatParser
from .interop_parsers import InteropProdParser, InteropTestParser

if TYPE_CHECKING:
    from ..config.oncall_config import OnCallConfiguration


class SlackMessageParserProvider:
    """Provides the appropriate Slack message parser based on product and environment."""

    def __init__(self):
        """Initialize the provider with all available parsers."""
        self._parsers: Dict[str, BaseSlackMessageParser] = {}
        self._register_default_parsers()

    def _register_default_parsers(self) -> None:
        """Register all default parsers."""
        # SEND parsers
        self.register_parser(SendProdParser())
        self.register_parser(SendUatParser())

        # INTEROP parsers
        self.register_parser(InteropProdParser())
        self.register_parser(InteropTestParser())

    def register_parser(self, parser: BaseSlackMessageParser) -> None:
        """
        Register a parser for a specific product-environment combination.

        Args:
            parser: The parser instance to register
        """
        key = parser.product_environment.key
        self._parsers[key] = parser

    def get_parser(self, product: str, environment: str, oncall_config: Optional['OnCallConfiguration'] = None) -> Optional[BaseSlackMessageParser]:
        """
        Get the appropriate parser for the given product and environment.

        Args:
            product: The product name (e.g., 'SEND', 'INTEROP')
            environment: The environment name (e.g., 'prod', 'uat', 'test')
            oncall_config: Optional oncall configuration for identifying oncall alarms

        Returns:
            The appropriate parser, or None if no suitable parser is found
        """
        # Create parser on-demand with oncall_config if provided
        product_upper = product.upper()
        env_lower = environment.lower()

        # Map product-environment combinations to parser classes
        parser_map = {
            'SEND_prod': SendProdParser,
            'SEND_uat': SendUatParser,
            'INTEROP_prod': InteropProdParser,
            'INTEROP_test': InteropTestParser,
        }

        # Try exact match first
        exact_key = f"{product_upper}_{env_lower}"
        if exact_key in parser_map:
            return parser_map[exact_key](oncall_config)

        # Fallback: try prod environment for the same product
        fallback_key = f"{product_upper}_prod"
        if fallback_key in parser_map:
            return parser_map[fallback_key](oncall_config)

        # No suitable parser found
        return None

    def get_available_combinations(self) -> list[str]:
        """
        Get a list of all available product-environment combinations.

        Returns:
            List of available combinations in format "PRODUCT_ENVIRONMENT"
        """
        return list(self._parsers.keys())

    def supports_combination(self, product: str, environment: str) -> bool:
        """
        Check if a product-environment combination is supported.

        Args:
            product: The product name
            environment: The environment name

        Returns:
            True if the combination is supported (either directly or via fallback)
        """
        return self.get_parser(product, environment) is not None

    def __str__(self) -> str:
        return f"SlackMessageParserProvider(parsers={len(self._parsers)})"

    def __repr__(self) -> str:
        return self.__str__()