"""Parallel Initialization System for AI Agents"""

import asyncio
import aiohttp
from typing import Dict, List, Set
from pathlib import Path
import logging
from rich.console import Console

class ParallelInitializer:
    """Handles parallel initialization of AI agents"""

    def __init__(self):
        self.console = Console()
        self.endpoints = {
            "tgpt": {"port": 4891, "specialty": "shell"},
            "lmstudio": {"port": 1234, "specialty": "routing"},
            "openinterpreter": {"port": 8080, "specialty": "execution"}
        }
        self.active_agents = set()
        self.state_cache = {}

    async def initialize_parallel(self) -> Dict[str, bool]:
        """Initialize all agents in parallel"""
        async with aiohttp.ClientSession() as session:
            init_tasks = [
                self._init_agent(session, name, config)
                for name, config in self.endpoints.items()
            ]
            results = await asyncio.gather(*init_tasks, return_exceptions=True)

            status = {
                name: isinstance(result, dict)
                for name, result in zip(self.endpoints.keys(), results)
            }

            self.active_agents = {k for k,v in status.items() if v}
            return status

    async def _init_agent(self,
                         session: aiohttp.ClientSession,
                         name: str,
                         config: Dict) -> Dict:
        """Initialize individual agent"""
        try:
            url = f"http://localhost:{config['port']}"
            async with session.post(
                f"{url}/init",
                json={"specialty": config["specialty"]},
                timeout=5
            ) as resp:
                return await resp.json()
        except Exception as e:
            logging.warning(f"Agent {name} init failed: {e}")
            return None

    async def verify_integration(self) -> Dict[str, bool]:
        """Verify integration between agents"""
        if not self.active_agents:
            await self.initialize_parallel()

        if not self.active_agents:
            raise RuntimeError("No active agents to integrate!")

        # Verify cross-agent communication
        async with aiohttp.ClientSession() as session:
            verify_tasks = [
                self._verify_agent_integration(session, agent)
                for agent in self.active_agents
            ]
            results = await asyncio.gather(*verify_tasks)

            return {
                agent: result
                for agent, result in zip(self.active_agents, results)
            }

    async def _verify_agent_integration(self,
                                      session: aiohttp.ClientSession,
                                      agent: str) -> bool:
        """Verify individual agent integration"""
        try:
            config = self.endpoints[agent]
            url = f"http://localhost:{config['port']}"

            # Test cross-agent communication
            async with session.post(
                f"{url}/verify_integration",
                json={"agents": list(self.active_agents - {agent})}
            ) as resp:
                result = await resp.json()
                return result.get("status") == "integrated"
        except Exception as e:
            logging.error(f"Integration verification failed for {agent}: {e}")
            return False

async def main():
    """Main entry point"""
    initializer = ParallelInitializer()
    console = Console()

    try:
        # Initialize agents
        status = await initializer.initialize_parallel()
        console.print(f"\nAgent initialization status: {status}")

        # Verify integration
        if initializer.active_agents:
            integration = await initializer.verify_integration()
            console.print(f"\nIntegration status: {integration}")
        else:
            console.print("\n[red]No agents initialized successfully!")

    except Exception as e:
        console.print(f"[red]Error during initialization: {e}")

if __name__ == "__main__":
    asyncio.run(main())
