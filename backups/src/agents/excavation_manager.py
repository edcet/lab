#!/usr/bin/env python3

"""Agent manager for the excavation system"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import numpy as np
from rich.console import Console

@dataclass
class Agent:
    """Represents an AI agent"""
    id: str
    type: str
    model: str
    capabilities: List[str]
    status: str = "initializing"
    current_task: Optional[Dict] = None
    progress: float = 0.0

class ExcavationManager:
    """Manages and coordinates AI agents"""

    def __init__(self, config_path: str):
        self.console = Console()
        self.config = self._load_config(config_path)
        self.agents: Dict[str, Agent] = {}
        self.task_queue = asyncio.Queue()
        self.results_queue = asyncio.Queue()
        self.pattern_queue = asyncio.Queue()

        # Setup logging
        logging.basicConfig(
            filename='manager.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def _load_config(self, path: str) -> Dict:
        """Load configuration from file"""
        with open(path) as f:
            return json.load(f)

    async def initialize_agents(self):
        """Initialize all agent types"""
        # Manager Agent (LM Studio - deepseek-reasoning-7b)
        await self._create_agent(
            "manager",
            "deepseek-reasoning-7b",
            ["coordination", "oversight", "pattern_analysis"]
        )

        # Architecture Agent (qwen2.5-coder-14b-instruct)
        await self._create_agent(
            "architect",
            "qwen2.5-coder-14b-instruct",
            ["design", "analysis", "integration"]
        )

        # Pattern Agent (deepthink-reasoning-7b)
        await self._create_agent(
            "pattern_analyst",
            "deepthink-reasoning-7b",
            ["pattern_detection", "synthesis", "learning"]
        )

        # Vision Agent (llama-3.2-11b-vision-instruct)
        await self._create_agent(
            "vision_analyst",
            "llama-3.2-11b-vision-instruct",
            ["visual_analysis", "diagram_understanding", "ui_evolution"]
        )

        # Tool Agent (toolgen-llama-3-8b-tool-retriever-g3)
        await self._create_agent(
            "tool_coordinator",
            "toolgen-llama-3-8b-tool-retriever-g3",
            ["tool_orchestration", "api_integration", "automation"]
        )

    async def _create_agent(self, agent_type: str, model: str, capabilities: List[str]):
        """Create and initialize an agent"""
        agent_id = f"{agent_type}_{len(self.agents)}"
        agent = Agent(
            id=agent_id,
            type=agent_type,
            model=model,
            capabilities=capabilities
        )
        self.agents[agent_id] = agent
        logging.info(f"Created agent: {agent}")

        # Register with safety system
        await self._register_with_safety(agent)

    async def _register_with_safety(self, agent: Agent):
        """Register agent with safety system"""
        # This will be implemented when we integrate with safety system
        pass

    async def start(self):
        """Start the excavation system"""
        try:
            # Initialize agents
            await self.initialize_agents()

            # Start monitoring tasks
            monitor_task = asyncio.create_task(self._monitor_agents())
            pattern_task = asyncio.create_task(self._monitor_patterns())
            resource_task = asyncio.create_task(self._monitor_resources())

            # Start agent tasks
            agent_tasks = [
                asyncio.create_task(self._run_agent(agent))
                for agent in self.agents.values()
            ]

            # Wait for all tasks
            await asyncio.gather(
                monitor_task,
                pattern_task,
                resource_task,
                *agent_tasks
            )

        except Exception as e:
            logging.error(f"Manager error: {e}")
            raise

    async def _run_agent(self, agent: Agent):
        """Run an individual agent"""
        while True:
            try:
                # Get next task
                task = await self._get_task_for_agent(agent)

                # Update agent status
                agent.status = "working"
                agent.current_task = task

                # Process task
                result = await self._process_task(agent, task)

                # Store result
                await self.results_queue.put({
                    "agent_id": agent.id,
                    "task": task,
                    "result": result,
                    "timestamp": datetime.now().timestamp()
                })

                # Update agent status
                agent.status = "idle"
                agent.current_task = None
                agent.progress = 0.0

            except Exception as e:
                logging.error(f"Agent {agent.id} error: {e}")
                agent.status = "error"
                await asyncio.sleep(5)  # Back off on error

    async def _get_task_for_agent(self, agent: Agent) -> Dict:
        """Get appropriate task for agent based on capabilities"""
        while True:
            task = await self.task_queue.get()

            # Check if agent can handle task
            if any(cap in agent.capabilities for cap in task["required_capabilities"]):
                return task

            # If not, put task back in queue
            await self.task_queue.put(task)
            await asyncio.sleep(1)

    async def _process_task(self, agent: Agent, task: Dict) -> Dict:
        """Process a task with appropriate model"""
        endpoint = self._get_endpoint_for_model(agent.model)

        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=task) as response:
                return await response.json()

    def _get_endpoint_for_model(self, model: str) -> str:
        """Get appropriate endpoint for model"""
        if "deepseek" in model or "qwen" in model:
            return "http://localhost:1234/v1/chat/completions"
        elif "llama" in model:
            return "http://localhost:11434/api/generate"
        else:
            return "http://localhost:1234/v1/chat/completions"  # Default to LM Studio

    async def _monitor_agents(self):
        """Monitor agent health and performance"""
        while True:
            try:
                for agent in self.agents.values():
                    # Check if agent is responsive
                    if agent.status == "working":
                        task_duration = (
                            datetime.now().timestamp() -
                            agent.current_task["start_time"]
                        )
                        if task_duration > 300:  # 5 minute timeout
                            logging.warning(f"Agent {agent.id} task timeout")
                            agent.status = "error"

                await asyncio.sleep(10)
            except Exception as e:
                logging.error(f"Agent monitoring error: {e}")
                await asyncio.sleep(5)

    async def _monitor_patterns(self):
        """Monitor for emerging patterns"""
        while True:
            try:
                # Get results and look for patterns
                while not self.results_queue.empty():
                    result = await self.results_queue.get()
                    patterns = await self._analyze_patterns(result)

                    # Store valuable patterns
                    for pattern in patterns:
                        await self.pattern_queue.put(pattern)

                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Pattern monitoring error: {e}")
                await asyncio.sleep(5)

    async def _analyze_patterns(self, result: Dict) -> List[Dict]:
        """Analyze results for patterns"""
        patterns = []

        # This is where we'll implement pattern analysis
        # For now, just log the result
        logging.info(f"Result received: {result}")

        return patterns

    async def _monitor_resources(self):
        """Monitor system resource usage"""
        while True:
            try:
                # Check memory usage
                memory_usage = psutil.virtual_memory().percent
                if memory_usage > 90:
                    logging.warning(f"High memory usage: {memory_usage}%")
                    await self._handle_high_memory()

                # Check CPU usage
                cpu_usage = psutil.cpu_percent()
                if cpu_usage > 80:
                    logging.warning(f"High CPU usage: {cpu_usage}%")
                    await self._handle_high_cpu()

                await asyncio.sleep(5)
            except Exception as e:
                logging.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(5)

    async def _handle_high_memory(self):
        """Handle high memory usage"""
        # Pause non-critical agents
        for agent in self.agents.values():
            if agent.type not in ["manager", "pattern_analyst"]:
                agent.status = "paused"

        # Clear caches
        # This will be implemented based on system needs

    async def _handle_high_cpu(self):
        """Handle high CPU usage"""
        # Reduce parallel operations
        # This will be implemented based on system needs
        pass

async def main():
    """Main entry point"""
    try:
        manager = ExcavationManager(".config/system/config.json")
        await manager.start()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    asyncio.run(main())
