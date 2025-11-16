"""
Product configuration data class.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from .environment_config import EnvironmentConfig
from .ignore_rule import IgnoreRule
from .oncall_config import OnCallConfiguration


@dataclass
class ProductConfig:
    """Configuration for a specific product."""
    name: str
    environments: Dict[str, EnvironmentConfig]
    ignore_rules: List[IgnoreRule]
    oncall_config: Optional[OnCallConfiguration] = None

    def get_environment_config(self, env_name: str) -> Optional[EnvironmentConfig]:
        """Get configuration for a specific environment."""
        return self.environments.get(env_name)

    def get_slack_channel_id(self, env_name: str) -> Optional[str]:
        """Get Slack channel ID for a specific environment."""
        env_config = self.get_environment_config(env_name)
        return env_config.slack_channel_id if env_config else None

    def get_applicable_ignore_rules(self, env_name: str) -> List[IgnoreRule]:
        """Get ignore rules that apply to a specific environment."""
        applicable_rules = []
        for rule in self.ignore_rules:
            if rule.applies_to_environment(env_name):
                applicable_rules.append(rule)
        return applicable_rules