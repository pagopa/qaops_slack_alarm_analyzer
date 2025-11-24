"""
Base interface for Slack message parsers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING

from .product_environment import ProductEnvironment

if TYPE_CHECKING:
    from ..config.oncall_config import OnCallConfiguration


class BaseSlackMessageParser(ABC):
    """Abstract base class for Slack message parsers."""

    def __init__(self, product_environment: ProductEnvironment, oncall_config: Optional['OnCallConfiguration'] = None):
        """
        Initialize the parser with product and environment information.

        Args:
            product_environment: The product-environment combination this parser handles
            oncall_config: Optional configuration for identifying oncall alarms
        """
        self.product_environment = product_environment
        self.oncall_config = oncall_config

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

    def is_oncall_alarm(self, alarm_name: str) -> bool:
        """
        Check if an alarm is an oncall alarm based on the configured pattern.

        Args:
            alarm_name: The name of the alarm to check

        Returns:
            bool: True if the alarm is identified as oncall
        """
        if not self.oncall_config:
            return False
        return self.oncall_config.is_oncall_alarm(alarm_name)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.product_environment})"

    def __repr__(self) -> str:
        return self.__str__()