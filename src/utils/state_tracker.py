"""State Tracker for AI Agent System"""

import asyncio
import aiohttp
from typing import Dict, List, Set, Any
from dataclasses import dataclass
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table
import logging
from pathlib import Path

@dataclass
class SystemState:
    """System state snapshot"""
    timestamp: datetime
    active_agents: Set[str]
    task_queue: List[str]
    agent_states: Dict[str, Dict]
    memory_usage: Dict[str, float]
    cpu_usage: Dict[str, float]

class StateTracker:
    """Tracks and monitors system state"""

    def __init__(self):
        self.console = Console()
        self.state_history: List[SystemState] = []
        self.current_state: SystemState = None
        self.alert_thresholds = {
            "memory": 0.9,  # 90% usage
            "cpu": 0.8,     # 80% usage
            "queue": 100    # 100 tasks
        }
        self._agent_ports = {
            "tgpt": 4891,
            "lmstudio": 1234,
            "openinterpreter": 8080
        }

    async def start_monitoring(self):
        """Start continuous state monitoring"""
        while True:
            try:
                # Gather state from all components
                state = await self._gather_state()
                self.current_state = state
                self.state_history.append(state)

                # Trim history if too long
                if len(self.state_history) > 1000:
                    self.state_history = self.state_history[-1000:]

                # Check for alerts
                await self._check_alerts(state)

                # Update display
                self._update_display(state)

                await asyncio.sleep(1)  # Update every second

            except Exception as e:
                logging.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)  # Back off on error

    def _get_port(self, agent: str) -> int:
        """Get agent port"""
        return self._agent_ports[agent]

    async def _gather_state(self) -> SystemState:
        """Gather state from all system components"""
        async with aiohttp.ClientSession() as session:
            agent_states = await self._gather_agent_states(session)
            return SystemState(
                timestamp=datetime.now(),
                active_agents=self._get_active_agents(agent_states),
                task_queue=await self._get_task_queue(),
                agent_states=agent_states,
                memory_usage=await self._get_memory_usage(),
                cpu_usage=await self._get_cpu_usage()
            )

    async def _gather_agent_states(self, session: aiohttp.ClientSession) -> Dict[str, Dict]:
        """Gather states from all agents"""
        agent_states = {}
        for agent in self._agent_ports.keys():
            try:
                async with session.get(f"http://localhost:{self._get_port(agent)}/state") as resp:
                    agent_states[agent] = await resp.json()
            except:
                agent_states[agent] = {"status": "unreachable"}
        return agent_states

    def _get_active_agents(self, agent_states: Dict[str, Dict]) -> Set[str]:
        """Get set of currently active agents"""
        return {
            agent for agent, state in agent_states.items()
            if state.get("status") != "unreachable"
        }

    async def _get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage for each component"""
        # This would normally use psutil or similar
        # For now, return mock data
        return {
            "tgpt": 0.3,
            "lmstudio": 0.4,
            "openinterpreter": 0.3
        }

    async def _get_cpu_usage(self) -> Dict[str, float]:
        """Get CPU usage for each component"""
        # This would normally use psutil or similar
        # For now, return mock data
        return {
            "tgpt": 0.2,
            "lmstudio": 0.3,
            "openinterpreter": 0.2
        }

    async def _get_task_queue(self) -> List[str]:
        """Get current task queue"""
        # This would normally check the actual queue
        # For now, return mock data
        return ["task1", "task2"]

    async def _check_alerts(self, state: SystemState):
        """Check for alert conditions"""
        alerts = []
        self._check_resource_alerts(state, alerts)
        self._check_queue_alerts(state, alerts)
        await self._handle_alerts(alerts)

    def _check_resource_alerts(self, state: SystemState, alerts: List[str]):
        """Check resource usage alerts"""
        for agent, usage in state.memory_usage.items():
            if usage > self.alert_thresholds["memory"]:
                alerts.append(f"High memory usage for {agent}: {usage*100}%")
        for agent, usage in state.cpu_usage.items():
            if usage > self.alert_thresholds["cpu"]:
                alerts.append(f"High CPU usage for {agent}: {usage*100}%")

    def _check_queue_alerts(self, state: SystemState, alerts: List[str]):
        """Check queue length alert"""
        if len(state.task_queue) > self.alert_thresholds["queue"]:
            alerts.append(f"Long task queue: {len(state.task_queue)} tasks")

    async def _handle_alerts(self, alerts: List[str]):
        """Log and print alerts"""
        for alert in alerts:
            logging.warning(alert)
            self.console.print(f"[yellow]ALERT: {alert}")

    def _update_display(self, state: SystemState):
        """Update console display"""
        table = Table(title="System State")

        # Add columns
        table.add_column("Component")
        table.add_column("Status")
        table.add_column("Memory")
        table.add_column("CPU")

        # Add rows
        for agent in ["tgpt", "lmstudio", "openinterpreter"]:
            status = "🟢" if agent in state.active_agents else "🔴"
            memory = f"{state.memory_usage[agent]*100:.1f}%"
            cpu = f"{state.cpu_usage[agent]*100:.1f}%"

            table.add_row(
                agent,
                status,
                memory,
                cpu
            )

        # Print table
        self.console.clear()
        self.console.print(table)

        # Print task queue
        self.console.print(f"\nTask Queue: {len(state.task_queue)} tasks")

async def main():
    """Main entry point"""
    tracker = StateTracker()
    console = Console()

    try:
        await tracker.start_monitoring()
    except Exception as e:
        console.print(f"[red]Error during monitoring: {e}")

if __name__ == "__main__":
    asyncio.run(main())
