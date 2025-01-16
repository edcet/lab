"""Neural Fabric Extended (NFX) CLI

Command-line interface for NFX operations.
"""

import click
import asyncio
import numpy as np
from typing import Dict, Any
import json
import logging

from ..core.compute.engine import ComputeEngine, ComputeConfig
from ..core.memory.manager import MemoryManager
from ..core.process.orchestrator import (
    Orchestrator,
    ProcessConfig,
    ProcessStats
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('nfx.cli')

class CLI:
    """NFX CLI handler"""

    def __init__(self):
        self.compute = ComputeEngine()
        self.memory = MemoryManager()
        self.orchestrator = Orchestrator()

    async def setup(self):
        """Initialize system"""
        # Register default processes
        await self._register_defaults()

    async def _register_defaults(self):
        """Register default processing nodes"""
        # Add basic processing nodes
        await self.orchestrator.register_process(
            ProcessConfig(
                name='preprocess',
                priority=1,
                resources={'cpu': 1, 'memory': 1024},
                timeout=5.0
            )
        )

        await self.orchestrator.register_process(
            ProcessConfig(
                name='process',
                priority=2,
                resources={'cpu': 2, 'memory': 2048},
                timeout=10.0
            )
        )

        await self.orchestrator.register_process(
            ProcessConfig(
                name='postprocess',
                priority=1,
                resources={'cpu': 1, 'memory': 1024},
                timeout=5.0
            )
        )

        # Connect nodes
        await self.orchestrator.connect_processes('preprocess', 'process')
        await self.orchestrator.connect_processes('process', 'postprocess')

@click.group()
def cli():
    """Neural Fabric eXtended (NFX) CLI"""
    pass

@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Configuration file path')
def start(config: str):
    """Start NFX system"""
    try:
        # Load config if provided
        if config:
            with open(config) as f:
                config_data = json.load(f)
        else:
            config_data = {}

        # Initialize and run system
        cli_handler = CLI()
        asyncio.run(cli_handler.setup())

        click.echo('NFX system started')

    except Exception as e:
        logger.error(f"Failed to start system: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument('data_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(),
              help='Output path for results')
def process(data_path: str, output: str):
    """Process data through NFX system"""
    try:
        # Load data
        data = np.load(data_path)

        # Initialize system
        cli_handler = CLI()

        # Process data
        results = asyncio.run(cli_handler.orchestrator.process(data))

        # Save results
        if output:
            np.save(output, results)
            click.echo(f'Results saved to {output}')
        else:
            click.echo(results)

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise click.ClickException(str(e))

@cli.command()
def stats():
    """Show system statistics"""
    try:
        # Initialize system
        cli_handler = CLI()

        # Get stats
        compute_stats = cli_handler.compute.get_stats()
        memory_stats = cli_handler.memory.get_stats()
        process_stats = cli_handler.orchestrator.get_stats()

        # Display stats
        click.echo("\nCompute Statistics:")
        click.echo(json.dumps(compute_stats, indent=2))

        click.echo("\nMemory Statistics:")
        click.echo(json.dumps(memory_stats.__dict__, indent=2))

        click.echo("\nProcess Statistics:")
        for name, stats in process_stats.items():
            click.echo(f"\n{name}:")
            click.echo(json.dumps(stats.__dict__, indent=2))

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument('name')
@click.option('--priority', type=int, default=1,
              help='Process priority (1-10)')
@click.option('--timeout', type=float, default=5.0,
              help='Process timeout in seconds')
def add_process(name: str, priority: int, timeout: float):
    """Add new process to system"""
    try:
        # Initialize system
        cli_handler = CLI()

        # Create process config
        config = ProcessConfig(
            name=name,
            priority=priority,
            resources={'cpu': 1, 'memory': 1024},
            timeout=timeout
        )

        # Register process
        asyncio.run(cli_handler.orchestrator.register_process(config))

        click.echo(f'Process {name} registered')

    except Exception as e:
        logger.error(f"Failed to add process: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument('from_process')
@click.argument('to_process')
def connect(from_process: str, to_process: str):
    """Connect two processes"""
    try:
        # Initialize system
        cli_handler = CLI()

        # Connect processes
        asyncio.run(cli_handler.orchestrator.connect_processes(
            from_process,
            to_process
        ))

        click.echo(f'Connected {from_process} to {to_process}')

    except Exception as e:
        logger.error(f"Failed to connect processes: {e}")
        raise click.ClickException(str(e))

if __name__ == '__main__':
    cli()
