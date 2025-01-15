"""Test runner for integration tests"""

import asyncio
import json
import yaml
import logging
import shutil
from pathlib import Path

def create_config_files(test_workspace: Path):
    """Create necessary configuration files for testing"""

    # Create config directories
    system_config_dir = test_workspace / ".config/system"
    ai_config_dir = test_workspace / ".config/ai"

    system_config_dir.mkdir(parents=True, exist_ok=True)
    ai_config_dir.mkdir(parents=True, exist_ok=True)

    # Create system config
    system_config = {
        "store": {
            "enabled": True,
            "db_path": str(test_workspace / ".data/store.db")
        },
        "model_gateway": {
            "enabled": True,
            "config_path": str(test_workspace / ".config/ai/config.yml")
        },
        "credential_manager": {
            "enabled": True,
            "store_path": str(test_workspace / ".data/credentials")
        },
        "health_monitor": {
            "enabled": True,
            "check_interval": 30
        }
    }

    with open(system_config_dir / "config.json", "w") as f:
        json.dump(system_config, f, indent=2)

    # Create AI config
    ai_config = {
        "backends": {
            "codellama": {
                "host": "localhost",
                "port": 11434,
                "capabilities": ["code_generation", "code_analysis", "pattern_detection"],
                "max_tokens": 2048,
                "temperature": 0.7
            },
            "mixtral": {
                "host": "localhost",
                "port": 1234,
                "capabilities": ["text_generation", "pattern_analysis", "context_understanding"],
                "max_tokens": 4096,
                "temperature": 0.8
            },
            "gpt4": {
                "host": "localhost",
                "port": 4891,
                "capabilities": ["code_generation", "text_generation", "pattern_detection"],
                "max_tokens": 8192,
                "temperature": 0.9
            }
        },
        "routing": {
            "strategy": "adaptive",
            "health_check_interval": 30,
            "max_retries": 3,
            "timeout": 10.0,
            "default_model": "codellama",
            "fallback_model": "mixtral"
        }
    }

    with open(ai_config_dir / "config.yml", "w") as f:
        yaml.dump(ai_config, f, default_flow_style=False)

    logging.info("Configuration files created successfully")

def setup_test_environment():
    """Set up test environment"""
    test_workspace = Path(".test_workspace")

    # Remove existing test workspace if it exists
    if test_workspace.exists():
        shutil.rmtree(test_workspace)

    # Create test workspace
    test_workspace.mkdir()

    try:
        create_config_files(test_workspace)
        logging.info("Test environment setup complete")
    except Exception as e:
        logging.error(f"Failed to set up test environment: {e}")
        raise

def cleanup_test_environment(test_workspace: Path):
    """Clean up test environment"""
    try:
        if test_workspace.exists():
            shutil.rmtree(test_workspace)
        logging.info("Test environment cleanup complete")
    except Exception as e:
        logging.error(f"Failed to clean up test environment: {e}")

async def run_tests():
    """Run integration tests"""
    test_workspace = Path(".test_workspace")

    try:
        # Set up test environment
        setup_test_environment()

        # Run tests with coverage
        import pytest
        pytest.main([
            "src/tests",
            "-v",
            "--asyncio-mode=strict",
            "--cov=src",
            "--cov-report=term-missing"
        ])
    finally:
        # Clean up
        cleanup_test_environment(test_workspace)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    asyncio.run(run_tests())
