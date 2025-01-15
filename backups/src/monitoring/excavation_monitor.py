#!/usr/bin/env python3

"""Real-time monitoring system for the excavation process"""

import asyncio
import psutil
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

class ExcavationMonitor:
    """Monitors and displays the excavation system status"""

    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.active_agents = {}
        self.patterns = []
        self.alerts = []

        # Configure layout
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1)
        )
        self.layout["main"].split_row(
            Layout(name="agents", ratio=2),
            Layout(name="patterns", ratio=2),
            Layout(name="metrics", ratio=1)
        )

    def generate_header(self) -> Panel:
        """Generate header with system status"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return Panel(
            f"Excavation System Monitor - {now}",
            style="bold white on blue"
        )

    def generate_agent_table(self) -> Table:
        """Generate table of active agents"""
        table = Table(title="Active Agents")
        table.add_column("Agent", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Task", style="yellow")
        table.add_column("Progress", style="magenta")

        for agent, info in self.active_agents.items():
            table.add_row(
                agent,
                info["status"],
                info["current_task"],
                f"{info['progress']}%"
            )

        return table

    def generate_pattern_panel(self) -> Panel:
        """Generate panel showing detected patterns"""
        pattern_text = Text()
        for pattern in self.patterns[-10:]:  # Show last 10 patterns
            pattern_text.append(
                f"• {pattern['type']}: {pattern['description']}\n",
                style="green"
            )
        return Panel(pattern_text, title="Emerging Patterns")

    def generate_metrics_panel(self) -> Panel:
        """Generate panel showing system metrics"""
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        metrics_text = Text()
        metrics_text.append(f"CPU: {cpu}%\n", style="cyan")
        metrics_text.append(f"Memory: {mem}%\n", style="magenta")
        metrics_text.append("\nActive Models:\n", style="yellow")
        metrics_text.append("- LM Studio\n", style="green")
        metrics_text.append("- Ollama\n", style="green")
        metrics_text.append("- TGPT\n", style="green")
        metrics_text.append("- Jan\n", style="green")
        return Panel(metrics_text, title="System Metrics")

    def update_display(self):
        """Update the display with current information"""
        self.layout["header"].update(self.generate_header())
        self.layout["agents"].update(self.generate_agent_table())
        self.layout["patterns"].update(self.generate_pattern_panel())
        self.layout["metrics"].update(self.generate_metrics_panel())

    async def monitor_agents(self):
        """Monitor agent activities"""
        while True:
            # Update agent information
            # This will be populated by the actual agents
            await asyncio.sleep(1)

    async def monitor_patterns(self):
        """Monitor emerging patterns"""
        while True:
            # Update pattern information
            # This will be populated by the pattern detection system
            await asyncio.sleep(1)

    async def start(self):
        """Start the monitoring system"""
        with Live(self.layout, refresh_per_second=1):
            while True:
                self.update_display()
                await asyncio.sleep(1)

async def main():
    monitor = ExcavationMonitor()
    await monitor.start()

if __name__ == "__main__":
    asyncio.run(main())
