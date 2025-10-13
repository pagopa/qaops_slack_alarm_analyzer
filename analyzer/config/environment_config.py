"""
Environment configuration data class.
"""
from dataclasses import dataclass


@dataclass
class EnvironmentConfig:
    """Configuration for a specific environment."""
    name: str
    slack_channel_id: str