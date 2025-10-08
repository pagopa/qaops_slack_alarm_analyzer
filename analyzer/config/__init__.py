"""
Configuration management package for QAOps Slack Alarm Analyzer.

This package contains all configuration-related classes and utilities:
- IgnoreRule: Define alarm filtering rules
- EnvironmentConfig: Environment-specific settings
- ProductConfig: Product-level configuration with environments and ignore rules
- IgnoreRuleParser: Parser for evaluating ignore rules against messages
- ConfigReader: YAML configuration file reader and parser (import separately)
"""

from .ignore_rule import IgnoreRule
from .environment_config import EnvironmentConfig
from .product_config import ProductConfig
from .ignore_rule_parser import IgnoreRuleParser

__all__ = [
    'IgnoreRule',
    'EnvironmentConfig',
    'ProductConfig',
    'IgnoreRuleParser'
]