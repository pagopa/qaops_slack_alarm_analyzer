"""
Provider for Slack message parsers based on product and environment.
"""
from typing import Dict, Optional

from .base_slack_parser import BaseSlackMessageParser
from .product_environment import ProductEnvironment
from .send_parsers import SendProdParser, SendUatParser
from .interop_parsers import InteropProdParser, InteropTestParser


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

    def get_parser(self, product: str, environment: str) -> Optional[BaseSlackMessageParser]:
        """
        Get the appropriate parser for the given product and environment.

        Args:
            product: The product name (e.g., 'SEND', 'INTEROP')
            environment: The environment name (e.g., 'prod', 'uat', 'test')

        Returns:
            The appropriate parser, or None if no suitable parser is found
        """
        # Try exact match first
        product_env = ProductEnvironment(product.upper(), environment.lower())
        exact_key = product_env.key

        if exact_key in self._parsers:
            return self._parsers[exact_key]

        # Fallback: try prod environment for the same product
        fallback_env = ProductEnvironment(product.upper(), "prod")
        fallback_key = fallback_env.key

        if fallback_key in self._parsers:
            return self._parsers[fallback_key]

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