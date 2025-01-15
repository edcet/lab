"""Command Line Interface for Enhanced AI System"""

import typer
import asyncio
from typing import Optional, List
from pathlib import Path
import json
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import track
import logging
from datetime import datetime

from ..system import EnhancedAISystem
from ..config.manager import ConfigurationManager
from ..monitoring.system import SystemMonitor

app = typer.Typer(help="Enhanced AI System Management CLI")
console = Console()

# Global system instance
system: Optional[EnhancedAISystem] = None
config_manager: Optional[ConfigurationManager] = None
monitor: Optional[SystemMonitor] = None

@app.command()
def init(
    config_path: Path = typer.Option(
        Path("~/.config/enhanced-ai-system"),
        help="Configuration directory path"
    ),
    workspace: Path = typer.Option(
        Path("~/enhanced-ai-workspace"),
        help="Workspace directory path"
    )
):
    """Initialize the Enhanced AI System"""
    async def _init():
        global system, config_manager, monitor
        
        try:
            # Expand paths
            config_path = config_path.expanduser()
            workspace = workspace.expanduser()
            
            # Create directories
            config_path.mkdir(parents=True, exist_ok=True)
            workspace.mkdir(parents=True, exist_ok=True)
            
            with console.status("Initializing system..."):
                # Initialize components
                config_manager = ConfigurationManager(config_path)
                await config_manager.initialize()
                
                monitor = SystemMonitor()
                await monitor.initialize()
                
                system = EnhancedAISystem(config_manager.get_config('system'))
                await system.initialize()
            
            console.print("[green]System initialized successfully!")
            
        except Exception as e:
            console.print(f"[red]Initialization failed: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_init())

@app.command()
def status():
    """Get system status and health"""
    async def _status():
        if not all([system, monitor]):
            console.print("[red]System not initialized. Run 'init' first.")
            raise typer.Exit(1)
        
        try:
            with console.status("Checking system status..."):
                # Get health status
                health = await monitor.check_health()
                
                # Get metrics
                metrics = await monitor.get_metrics()
                
                # Create status table
                table = Table(title="System Status")
                table.add_column("Component")
                table.add_column("Status")
                table.add_column("Metrics")
                
                for component, status in health.components.items():
                    component_metrics = metrics['components'].get(component, {})
                    table.add_row(
                        component,
                        "[green]✓" if status else "[red]✗",
                        "\n".join(
                            f"{k}: {v:.2f}"
                            for k, v in component_metrics.items()
                        )
                    )
                
                console.print(table)
                
                # Show resource usage
                resource_table = Table(title="Resource Usage")
                resource_table.add_column("Resource")
                resource_table.add_column("Usage")
                
                for resource, usage in metrics['resources'].items():
                    if isinstance(usage, (int, float)):
                        resource_table.add_row(
                            resource,
                            f"{usage*100:.1f}%"
                        )
                
                console.print(resource_table)
                
                # Show issues if any
                if health.issues:
                    console.print("\n[yellow]Issues:")
                    for issue in health.issues:
                        console.print(f"  • {issue}")
                
        except Exception as e:
            console.print(f"[red]Error getting status: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_status())

@app.command()
def run(
    task_file: Path = typer.Argument(
        ...,
        help="Path to task configuration file"
    )
):
    """Run a task"""
    async def _run():
        if not system:
            console.print("[red]System not initialized. Run 'init' first.")
            raise typer.Exit(1)
        
        try:
            # Load task configuration
            with open(task_file) as f:
                if task_file.suffix == '.json':
                    task = json.load(f)
                elif task_file.suffix in ['.yml', '.yaml']:
                    task = yaml.safe_load(f)
                else:
                    raise ValueError("Unsupported file format")
            
            with console.status("Processing task..."):
                # Execute task
                result = await system.process_task(task)
                
                if result['success']:
                    console.print("[green]Task completed successfully!")
                    console.print(result['result'])
                else:
                    console.print(f"[red]Task failed: {result['error']}")
                
                # Show metrics
                metrics_table = Table(title="Task Metrics")
                metrics_table.add_column("Metric")
                metrics_table.add_column("Value")
                
                for metric, value in result['metrics'].items():
                    metrics_table.add_column(
                        metric,
                        str(value)
                    )
                
                console.print(metrics_table)
                
        except Exception as e:
            console.print(f"[red]Error running task: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_run())

@app.command()
def config(
    action: str = typer.Argument(
        ...,
        help="Action to perform (get/set/list)"
    ),
    config_type: Optional[str] = typer.Option(
        None,
        help="Configuration type (system/model/tool)"
    ),
    name: Optional[str] = typer.Option(
        None,
        help="Configuration name"
    ),
    value: Optional[str] = typer.Option(
        None,
        help="Configuration value (for set)"
    )
):
    """Manage system configuration"""
    async def _config():
        if not config_manager:
            console.print("[red]System not initialized. Run 'init' first.")
            raise typer.Exit(1)
        
        try:
            if action == "list":
                # List configurations
                table = Table(title="System Configuration")
                table.add_column("Type")
                table.add_column("Name")
                table.add_column("Value")
                
                for cfg_type in ['system', 'models', 'tools']:
                    config = config_manager.get_config(cfg_type)
                    if isinstance(config, dict):
                        for name, value in config.items():
                            table.add_row(
                                cfg_type,
                                name,
                                str(value)
                            )
                
                console.print(table)
                
            elif action == "get":
                if not config_type:
                    console.print("[red]Configuration type required for get")
                    raise typer.Exit(1)
                
                config = config_manager.get_config(config_type, name)
                console.print(yaml.safe_dump(config))
                
            elif action == "set":
                if not all([config_type, name, value]):
                    console.print(
                        "[red]Configuration type, name, and value required for set"
                    )
                    raise typer.Exit(1)
                
                # Parse value
                try:
                    value = json.loads(value)
                except:
                    pass  # Keep as string if not JSON
                
                await config_manager.update_config(
                    config_type,
                    {name: value}
                )
                console.print("[green]Configuration updated successfully!")
                
            else:
                console.print(f"[red]Unknown action: {action}")
                raise typer.Exit(1)
                
        except Exception as e:
            console.print(f"[red]Configuration error: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_config())

@app.command()
def monitor(
    refresh: int = typer.Option(
        5,
        help="Refresh interval in seconds"
    )
):
    """Monitor system in real-time"""
    async def _monitor():
        if not monitor:
            console.print("[red]System not initialized. Run 'init' first.")
            raise typer.Exit(1)
        
        try:
            with Progress() as progress:
                # Create progress tasks
                cpu_task = progress.add_task("[red]CPU Usage", total=100)
                mem_task = progress.add_task("[green]Memory Usage", total=100)
                
                while True:
                    # Get metrics
                    metrics = await monitor.get_metrics()
                    
                    # Update progress bars
                    progress.update(
                        cpu_task,
                        completed=metrics['resources']['cpu']*100
                    )
                    progress.update(
                        mem_task,
                        completed=metrics['resources']['memory']*100
                    )
                    
                    # Show component status
                    table = Table(title="Component Status")
                    table.add_column("Component")
                    table.add_column("Status")
                    table.add_column("Metrics")
                    
                    for component, component_metrics in metrics['components'].items():
                        table.add_row(
                            component,
                            "[green]Healthy" if component_metrics.get('error_rate', 0) < 0.1
                            else "[red]Unhealthy",
                            "\n".join(
                                f"{k}: {v:.2f}"
                                for k, v in component_metrics.items()
                            )
                        )
                    
                    console.clear()
                    console.print(table)
                    
                    await asyncio.sleep(refresh)
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped")
        except Exception as e:
            console.print(f"[red]Monitoring error: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_monitor())

@app.command()
def cleanup():
    """Cleanup system resources"""
    async def _cleanup():
        if not all([system, config_manager, monitor]):
            console.print("[red]System not initialized. Nothing to clean up.")
            return
        
        try:
            with console.status("Cleaning up system resources..."):
                # Cleanup components
                await asyncio.gather(
                    system.cleanup(),
                    config_manager.cleanup(),
                    monitor.cleanup()
                )
            
            console.print("[green]System cleanup completed successfully!")
            
        except Exception as e:
            console.print(f"[red]Cleanup error: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_cleanup())

def main():
    """Main entry point"""
    app()

if __name__ == "__main__":
    main()
