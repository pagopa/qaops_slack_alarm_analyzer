"""
Base interface for Slack message parsers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from .product_environment import ProductEnvironment


class BaseSlackMessageParser(ABC):
    """Abstract base class for Slack message parsers."""

    def __init__(self, product_environment: ProductEnvironment):
        """
        Initialize the parser with product and environment information.

        Args:
            product_environment: The product-environment combination this parser handles
        """
        self.product_environment = product_environment

    @abstractmethod
    def extract_alarm_info(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract alarm information from a Slack message.

        Args:
            message: The Slack message dictionary

        Returns:
            Dictionary containing extracted alarm info, or None if not an alarm message
        """
        pass

    @property
    def product(self) -> str:
        """Get the product this parser handles."""
        return self.product_environment.product

    @property
    def environment(self) -> str:
        """Get the environment this parser handles."""
        return self.product_environment.environment

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.product_environment})"

    def __repr__(self) -> str:
        return self.__str__()