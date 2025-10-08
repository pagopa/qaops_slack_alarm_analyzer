"""
Analyzer parameters data class for organizing analysis configuration.
"""
from dataclasses import dataclass
from typing import List, Optional

from analyzer.config.ignore_rule import IgnoreRule
from .config.product_config import ProductConfig

@dataclass
class AnalyzerParams:
    """Parameters for alarm analysis operations."""
    date_str: str
    product: str
    environment: str
    slack_channel_id: str
    oldest: float
    latest: float
    product_config: ProductConfig
    slack_token: Optional[str] = None

    def __post_init__(self):
        """Validate parameters after initialization."""
        if not self.date_str:
            raise ValueError("date_str cannot be empty")
        if not self.product:
            raise ValueError("product cannot be empty")
        if not self.environment:
            raise ValueError("environment cannot be empty")
        if not self.slack_channel_id:
            raise ValueError("slack_channel_id cannot be empty")
        if not self.product_config:
            raise ValueError("product_config cannot be None")
        if self.oldest >= self.latest:
            raise ValueError("oldest timestamp must be less than latest timestamp")

    @property
    def product_upper(self) -> str:
        """Get product name in uppercase."""
        return self.product.upper()

    @property
    def environment_upper(self) -> str:
        """Get environment name in uppercase."""
        return self.environment.upper()
    
    @property
    def product_rules(self) -> List[IgnoreRule]:
        return self.product_config.get_applicable_ignore_rules(self.environment)
 
    def __str__(self) -> str:
        return f"AnalyzerParams(date={self.date_str}, product={self.product}, env={self.environment})"

    def __repr__(self) -> str:
        return self.__str__()