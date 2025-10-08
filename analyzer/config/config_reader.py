"""
Configuration reader for loading product settings from base.yaml file.
"""
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from .environment_config import EnvironmentConfig
from .product_config import ProductConfig
from .ignore_rule import IgnoreRule


class ConfigReader:
    """Reads and parses the base.yaml configuration file."""

    def __init__(self, config_path: str = "config/base.yaml"):
        """
        Initialize the config reader.

        Args:
            config_path: Path to the base.yaml configuration file
        """
        self.config_path = Path(config_path)
        self._config_data: Optional[Dict[str, Any]] = None
        self._products: Optional[Dict[str, ProductConfig]] = None

    def load_config(self) -> None:
        """Load configuration from the YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config_data = yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error reading configuration file: {e}")

        if not self._config_data or 'products' not in self._config_data:
            raise ValueError("Configuration file must contain a 'products' section")

        self._parse_products()

    def _parse_products(self) -> None:
        """Parse product configurations from the loaded YAML data."""
        self._products = {}
        products_data = self._config_data['products']

        for product_name, product_data in products_data.items():
            # Parse environments
            environments = {}
            envs_data = product_data.get('envs', {})
            for env_name, env_data in envs_data.items():
                slack_channel_id = env_data.get('slack_channel_id', '')
                environments[env_name] = EnvironmentConfig(
                    name=env_name,
                    slack_channel_id=slack_channel_id
                )

            # Parse ignore rules
            ignore_rules = []
            alarms_data = product_data.get('alarms', {})
            ignore_data = alarms_data.get('ignore', [])

            for rule_data in ignore_data:
                if isinstance(rule_data, dict):
                    name = rule_data.get('name', '')
                    path = rule_data.get('path', '*')
                    environments_list = rule_data.get('environments', [])
                    reason = rule_data.get('reason', None)

                    if name:  # Only create rule if name is provided
                        ignore_rule = IgnoreRule(
                            pattern=name,
                            path=path,
                            environments=environments_list,
                            reason=reason
                        )
                        ignore_rules.append(ignore_rule)

            # Create product configuration
            self._products[product_name] = ProductConfig(
                name=product_name,
                environments=environments,
                ignore_rules=ignore_rules
            )

    def get_product_config(self, product_name: str) -> Optional[ProductConfig]:
        """
        Get configuration for a specific product.

        Args:
            product_name: Name of the product

        Returns:
            ProductConfig object or None if product not found
        """
        if self._products is None:
            self.load_config()

        return self._products.get(product_name)

    def get_all_products(self) -> Dict[str, ProductConfig]:
        """
        Get all product configurations.

        Returns:
            Dictionary mapping product names to ProductConfig objects
        """
        if self._products is None:
            self.load_config()

        return self._products.copy()

    def get_product_names(self) -> List[str]:
        """
        Get list of all product names.

        Returns:
            List of product names
        """
        if self._products is None:
            self.load_config()

        return list(self._products.keys())

    def get_environment_names(self, product_name: str) -> List[str]:
        """
        Get list of environment names for a specific product.

        Args:
            product_name: Name of the product

        Returns:
            List of environment names
        """
        product_config = self.get_product_config(product_name)
        if product_config:
            return list(product_config.environments.keys())
        return []

    def get_slack_channel_id(self, product_name: str, env_name: str) -> Optional[str]:
        """
        Get Slack channel ID for a specific product and environment.

        Args:
            product_name: Name of the product
            env_name: Name of the environment

        Returns:
            Slack channel ID or None if not found
        """
        product_config = self.get_product_config(product_name)
        if product_config:
            return product_config.get_slack_channel_id(env_name)
        return None

    def reload_config(self) -> None:
        """Reload configuration from file (useful for runtime updates)."""
        self._config_data = None
        self._products = None
        self.load_config()

    def validate_config(self) -> List[str]:
        """
        Validate the configuration and return any validation errors.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if self._products is None:
            try:
                self.load_config()
            except Exception as e:
                return [f"Failed to load configuration: {e}"]

        for product_name, product_config in self._products.items():
            # Validate that each product has at least one environment
            if not product_config.environments:
                errors.append(f"Product '{product_name}' has no environments defined")

            # Validate environment configurations
            for env_name, env_config in product_config.environments.items():
                if not env_config.slack_channel_id:
                    errors.append(f"Product '{product_name}', environment '{env_name}' has empty slack_channel_id")

            # Validate ignore rules
            for i, rule in enumerate(product_config.ignore_rules):
                if not rule.pattern:
                    errors.append(f"Product '{product_name}', ignore rule {i+1} has empty pattern")

        return errors