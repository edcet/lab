import asyncio
import logging
import json
import shutil
from pathlib import Path
import pytest
import sys
from contextlib import contextmanager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

class OptimizedEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def __init__(self):
        super().__init__()
        self._loop = None

    def get_event_loop(self):
        if self._loop is None:
            self._loop = self.new_event_loop()
            self._loop.set_exception_handler(self._handle_exception)
        return self._loop

    def _handle_exception(self, loop, context):
        msg = context.get('message', '')
        if 'exception' in context:
            exc = context['exception']
            logging.error(f'Async error: {msg}, Exception: {exc}')
        else:
            logging.error(f'Async error: {msg}')

@contextmanager
def event_loop_context():
    """Manage event loop lifecycle with proper cleanup."""
    policy = OptimizedEventLoopPolicy()
    asyncio.set_event_loop_policy(policy)
    loop = policy.get_event_loop()
    try:
        yield loop
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

def create_config_files(test_workspace: Path):
    """Create necessary configuration files for testing."""
    system_config_dir = test_workspace / ".config/system"
    ai_config_dir = test_workspace / ".config/ai"

    system_config_dir.mkdir(parents=True, exist_ok=True)
    ai_config_dir.mkdir(parents=True, exist_ok=True)

    # Create optimized system config
    system_config = {
        "components": {
            "store": {
                "enabled": True,
                "parallel": True,
                "dependencies": [],
                "health_check": True,
                "startup_timeout": 30,
                "retry_count": 3,
                "batch_size": 100  # Optimized batch size
            },
            "model_gateway": {
                "enabled": True,
                "parallel": True,
                "dependencies": ["store"],
                "health_check": True,
                "startup_timeout": 30,
                "retry_count": 3,
                "max_concurrent_requests": 50  # Optimized concurrency
            },
            "health_monitor": {
                "enabled": True,
                "parallel": True,
                "dependencies": [],
                "startup_timeout": 30,
                "retry_count": 3,
                "check_interval": 5  # Optimized interval
            }
        },
        "optimization": {
            "task_batching": True,
            "max_parallel_tasks": 100,
            "memory_limit": "1G",
            "resource_pooling": True
        }
    }

    with open(system_config_dir / "config.json", "w") as f:
        json.dump(system_config, f, indent=2)

    # Create AI config
    ai_config = {
        "providers": {
            "ollama": {
                "endpoint": "http://localhost:11434",
                "models": ["codellama"]
            },
            "lm_studio": {
                "endpoint": "http://localhost:1234",
                "models": ["mixtral"]
            },
            "tgpt": {
                "endpoint": "http://localhost:4891",
                "models": ["gpt4"]
            }
        }
    }

    with open(ai_config_dir / "config.yml", "w") as f:
        json.dump(ai_config, f, indent=2)

    logging.info("Configuration files created successfully")

def setup_test_environment():
    """Set up the test environment."""
    test_workspace = Path(".test_workspace")
    if test_workspace.exists():
        shutil.rmtree(test_workspace)
    test_workspace.mkdir()

    create_config_files(test_workspace)
    logging.info("Test environment setup complete")

def cleanup_test_environment():
    """Clean up the test environment."""
    test_workspace = Path(".test_workspace")
    if test_workspace.exists():
        shutil.rmtree(test_workspace)
    logging.info("Test environment cleanup complete")

def run_tests():
    """Run the integration tests with optimized resource handling."""
    logging.info("Starting integration tests")

    with event_loop_context() as loop:
        # Run tests with optimization settings
        args = [
            "-v",
            "--asyncio-mode=strict",
            "--cov=src",
            "--cov-report=term-missing",
            "-n", "auto",  # Parallel test execution
            "--max-worker-restart=0",
            "test_integration.py"
        ]

        return pytest.main(args)

if __name__ == "__main__":
    try:
        setup_test_environment()
        exit_code = run_tests()
    finally:
        cleanup_test_environment()

    sys.exit(exit_code)
