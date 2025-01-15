"""Configuration loader for AI gateway"""

import yaml
from pathlib import Path
from typing import Dict, Optional
from ..gateway.controller import GatewayConfig

class ConfigLoader:
    """Loads and validates gateway configuration"""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(".config/ai")

    def load_gateway_config(self) -> GatewayConfig:
        """Load the gateway configuration"""
        try:
            # Load base config
            config_path = self.config_dir / "base.yml"
            if not config_path.exists():
                raise FileNotFoundError(f"Config not found at {config_path}")

            with open(config_path) as f:
                config = yaml.safe_load(f)

            return GatewayConfig(
                providers=config.get("providers", {}),
                routing_strategy=config.get("routing_strategy", "adaptive"),
                health_check_interval=config.get("health_check_interval", 30),
                metrics_enabled=config.get("metrics_enabled", True)
            )

        except Exception as e:
            raise Exception(f"Failed to load gateway config: {e}")
