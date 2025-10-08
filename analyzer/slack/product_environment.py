"""
Product and environment parameter class for Slack message parsing.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProductEnvironment:
    """Immutable data class representing a product-environment combination."""
    product: str
    environment: str

    def __post_init__(self):
        """Validate parameters after initialization."""
        if not self.product:
            raise ValueError("product cannot be empty")
        if not self.environment:
            raise ValueError("environment cannot be empty")

    @property
    def product_upper(self) -> str:
        """Get product name in uppercase."""
        return self.product.upper()

    @property
    def environment_upper(self) -> str:
        """Get environment name in uppercase."""
        return self.environment.upper()

    @property
    def key(self) -> str:
        """Get a unique key for this product-environment combination."""
        return f"{self.product_upper}_{self.environment_upper}"

    def __str__(self) -> str:
        return f"{self.product}:{self.environment}"

    def __repr__(self) -> str:
        return f"ProductEnvironment(product='{self.product}', environment='{self.environment}')"