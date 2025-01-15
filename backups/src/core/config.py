"""Configuration Management

This module provides unified configuration loading and validation.
"""

import os
from pathlib import Path
import json
import yaml
from typing import Dict, Any, Optional
import logging

class ConfigurationManager:
    """Unified configuration management"""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self.config_root = self.workspace_root / ".config"
        self.loaded_configs = {}

    # Configuration Schemas
    SYSTEM_CONFIG_SCHEMA = {
        "type": "object",
        "required": ["monitoring", "paths", "models"],
        "properties": {
            "monitoring": {
                "type": "object",
                "required": ["log_level", "log_rotation"],
                "properties": {
                    "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
                    "log_rotation": {
                        "type": "object",
                        "required": ["enabled", "max_size", "backup_count"],
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "max_size": {"type": "string", "pattern": "^[0-9]+M$"},
                            "backup_count": {"type": "integer", "minimum": 1}
                        }
                    }
                }
            },
            "paths": {
                "type": "object",
                "required": ["logs", "data", "models"],
                "properties": {
                    "logs": {"type": "string"},
                    "data": {"type": "string"},
                    "models": {"type": "string"}
                }
            },
            "models": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "endpoint", "capabilities"],
                    "properties": {
                        "name": {"type": "string"},
                        "endpoint": {"type": "string", "format": "uri"},
                        "capabilities": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            }
        }
    }

    AI_CONFIG_SCHEMA = {
        "type": "object",
        "required": ["models", "endpoints", "parameters"],
        "properties": {
            "models": {
                "type": "object",
                "patternProperties": {
                    "^[a-zA-Z0-9_]+$": {
                        "type": "object",
                        "required": ["type", "context_size"],
                        "properties": {
                            "type": {"type": "string"},
                            "context_size": {"type": "integer", "minimum": 1},
                            "parameters": {"type": "object"}
                        }
                    }
                }
            },
            "endpoints": {
                "type": "object",
                "patternProperties": {
                    "^[a-zA-Z0-9_]+$": {
                        "type": "object",
                        "required": ["url", "auth_type"],
                        "properties": {
                            "url": {"type": "string", "format": "uri"},
                            "auth_type": {"type": "string", "enum": ["none", "basic", "bearer", "api_key"]}
                        }
                    }
                }
            },
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature": {"type": "number", "minimum": 0, "maximum": 1},
                    "top_p": {"type": "number", "minimum": 0, "maximum": 1},
                    "max_tokens": {"type": "integer", "minimum": 1}
                }
            }
        }
    }

    def load_system_config(self) -> Dict[str, Any]:
        """Load system configuration"""
        path = self.config_root / "system/config.json"
        config = self._load_json(path)
        if not self.validate_config(config, self.SYSTEM_CONFIG_SCHEMA):
            raise ValueError("Invalid system configuration")
        return config

    def load_ai_config(self) -> Dict[str, Any]:
        """Load AI configuration"""
        path = self.config_root / "ai/config.yml"
        config = self._load_yaml(path)
        if not self.validate_config(config, self.AI_CONFIG_SCHEMA):
            raise ValueError("Invalid AI configuration")
        return config

    def load_git_config(self) -> Dict[str, Any]:
        """Load git-autobuilder configuration"""
        path = self.config_root / "git-autobuilder/config.toml"
        return self._load_toml(path)

    def get_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a loaded configuration by name"""
        return self.loaded_configs.get(name)

    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load and parse JSON configuration"""
        try:
            if not path.exists():
                raise FileNotFoundError(f"Configuration file not found: {path}")

            with open(path) as f:
                config = json.load(f)
                self.loaded_configs[path.parent.name] = config
                return config

        except Exception as e:
            logging.error(f"Failed to load JSON config {path}: {e}")
            raise

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load and parse YAML configuration"""
        try:
            if not path.exists():
                raise FileNotFoundError(f"Configuration file not found: {path}")

            with open(path) as f:
                config = yaml.safe_load(f)
                self.loaded_configs[path.parent.name] = config
                return config

        except Exception as e:
            logging.error(f"Failed to load YAML config {path}: {e}")
            raise

    def _load_toml(self, path: Path) -> Dict[str, Any]:
        """Load and parse TOML configuration"""
        try:
            if not path.exists():
                raise FileNotFoundError(f"Configuration file not found: {path}")

            import toml
            with open(path) as f:
                config = toml.load(f)
                self.loaded_configs[path.parent.name] = config
                return config

        except Exception as e:
            logging.error(f"Failed to load TOML config {path}: {e}")
            raise

    def validate_config(self, config: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate configuration against schema"""
        try:
            from jsonschema import validate
            validate(instance=config, schema=schema)
            return True
        except Exception as e:
            logging.error(f"Config validation failed: {e}")
            return False
