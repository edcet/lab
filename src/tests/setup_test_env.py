import json
import os
from pathlib import Path

def setup_test_environment():
    """Set up test environment with necessary directories and configuration files."""
    # Create test workspace and config directories
    workspace_root = Path(".test_workspace")
    config_dir = workspace_root / ".config"
    system_config_dir = config_dir / "system"
    ai_config_dir = config_dir / "ai"

    for directory in [workspace_root, config_dir, system_config_dir, ai_config_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    # Create system configuration
    system_config = {
        "components": {
            "store": {
                "enabled": True,
                "parallel": True,
                "batch_size": 100,
                "cache_size": 1000,
                "db_path": str(workspace_root / "store.db")
            },
            "model_gateway": {
                "enabled": True,
                "parallel": True,
                "max_concurrent": 10,
                "providers": {
                    "ollama": {"endpoint": "http://localhost:11434"},
                    "lm_studio": {"endpoint": "http://localhost:1234"},
                    "tgpt": {"endpoint": "http://localhost:4891"}
                }
            },
            "health_monitor": {
                "enabled": True,
                "check_interval": 30,
                "metrics_port": 9090
            }
        },
        "security": {
            "encryption": {
                "enabled": True,
                "key_rotation_interval": 86400
            }
        }
    }

    with open(system_config_dir / "config.json", "w") as f:
        json.dump(system_config, f, indent=2)

    # Create AI configuration
    ai_config = {
        "providers": {
            "ollama": {
                "models": ["codellama", "llama2"],
                "capabilities": ["code", "text"]
            },
            "lm_studio": {
                "models": ["mixtral"],
                "capabilities": ["code", "text", "analysis"]
            },
            "tgpt": {
                "models": ["gpt4"],
                "capabilities": ["code", "text", "analysis"]
            }
        },
        "routing": {
            "default_provider": "ollama",
            "capability_routing": True,
            "load_balancing": True
        }
    }

    with open(ai_config_dir / "config.yml", "w") as f:
        json.dump(ai_config, f, indent=2)

if __name__ == "__main__":
    setup_test_environment()
    print("Test environment setup complete.")
