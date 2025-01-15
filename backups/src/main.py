"""Main entry point for the system"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict

from core.unified_system import UnifiedSystem
from core.config import ConfigurationManager

def setup_logging(config: Dict) -> None:
    """Setup logging based on configuration"""
    log_config = config["monitoring"]
    log_dir = Path(config["paths"]["logs"])
    log_dir.mkdir(exist_ok=True)

    handlers = [
        logging.StreamHandler(sys.stdout)
    ]

    if log_config["log_rotation"]["enabled"]:
        from logging.handlers import RotatingFileHandler
        handlers.append(
            RotatingFileHandler(
                log_dir / "system.log",
                maxBytes=int(log_config["log_rotation"]["max_size"].replace("M", "")) * 1024 * 1024,
                backupCount=log_config["log_rotation"]["backup_count"]
            )
        )

    logging.basicConfig(
        level=getattr(logging, log_config["log_level"]),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers
    )

async def main():
    """Main entry point"""
    try:
        # Get workspace root
        workspace_root = os.getenv("WORKSPACE_ROOT", ".")

        # Initialize configuration
        config_manager = ConfigurationManager(workspace_root)
        system_config = config_manager.load_system_config()

        # Setup logging
        setup_logging(system_config)
        logger = logging.getLogger(__name__)
        logger.info("Starting system initialization...")

        # Initialize core system
        system = UnifiedSystem(workspace_root)
        await system.start()
        logger.info("System started successfully")

        # Keep system running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        await system.stop()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
