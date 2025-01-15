#!/usr/bin/env python3

"""Launch script for the excavation system"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, List
from rich.console import Console
from rich.panel import Panel

# Import our components
from monitoring.excavation_monitor import ExcavationMonitor
from safety.excavation_safety import ExcavationSafety
from agents.excavation_manager import ExcavationManager

class ExcavationLauncher:
    """Launches and coordinates all excavation system components"""

    def __init__(self):
        self.console = Console()
        self.monitor = None
        self.safety = None
        self.manager = None
        self.running = True

        # Setup logging
        logging.basicConfig(
            filename='excavation.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        self.console.print("\n[yellow]Initiating graceful shutdown...[/yellow]")
        self.running = False

    async def verify_environment(self) -> bool:
        """Verify all required services are running"""
        try:
            # Check LM Studio
            self.console.print("Checking LM Studio... ", end="")
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:1234/v1/models") as resp:
                    if resp.status == 200:
                        self.console.print("[green]OK[/green]")
                    else:
                        self.console.print("[red]Failed[/red]")
                        return False

            # Check Ollama
            self.console.print("Checking Ollama... ", end="")
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/version") as resp:
                    if resp.status == 200:
                        self.console.print("[green]OK[/green]")
                    else:
                        self.console.print("[red]Failed[/red]")
                        return False

            # Check TGPT
            self.console.print("Checking TGPT... ", end="")
            if any("tgpt" in p.name() for p in psutil.process_iter()):
                self.console.print("[green]OK[/green]")
            else:
                self.console.print("[red]Failed[/red]")
                return False

            # Check Jan
            self.console.print("Checking Jan... ", end="")
            if any("jan" in p.name() for p in psutil.process_iter()):
                self.console.print("[green]OK[/green]")
            else:
                self.console.print("[red]Failed[/red]")
                return False

            return True

        except Exception as e:
            logging.error(f"Environment verification failed: {e}")
            return False

    async def start(self):
        """Start all system components"""
        try:
            # Print welcome message
            self.console.print(Panel(
                "[bold blue]Excavation System Launcher[/bold blue]\n\n"
                "Starting up all components...",
                expand=False
            ))

            # Verify environment
            if not await self.verify_environment():
                self.console.print("[red]Environment verification failed[/red]")
                return

            # Start safety system first
            self.console.print("\nStarting safety system...")
            self.safety = ExcavationSafety("/Users/him/lab")
            safety_task = asyncio.create_task(self.safety.start_monitoring())

            # Start monitoring system
            self.console.print("Starting monitoring system...")
            self.monitor = ExcavationMonitor()
            monitor_task = asyncio.create_task(self.monitor.start())

            # Start agent manager
            self.console.print("Starting agent manager...")
            self.manager = ExcavationManager(".config/system/config.json")
            manager_task = asyncio.create_task(self.manager.start())

            # Wait for all components
            await asyncio.gather(
                safety_task,
                monitor_task,
                manager_task
            )

        except Exception as e:
            logging.error(f"Startup error: {e}")
            self.console.print(f"[red]Error during startup: {e}[/red]")
            raise

    async def shutdown(self):
        """Gracefully shutdown all components"""
        try:
            self.console.print("\n[yellow]Shutting down...[/yellow]")

            # Stop agent manager first
            if self.manager:
                self.console.print("Stopping agent manager...")
                # Implement manager shutdown

            # Stop monitoring system
            if self.monitor:
                self.console.print("Stopping monitoring system...")
                # Implement monitor shutdown

            # Stop safety system last
            if self.safety:
                self.console.print("Stopping safety system...")
                # Implement safety shutdown

            self.console.print("[green]Shutdown complete[/green]")

        except Exception as e:
            logging.error(f"Shutdown error: {e}")
            self.console.print(f"[red]Error during shutdown: {e}[/red]")
            raise

async def main():
    launcher = ExcavationLauncher()
    try:
        await launcher.start()
        while launcher.running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await launcher.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
