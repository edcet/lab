"""Integration Orchestrator for AI Agents"""

import asyncio
import aiohttp
from typing import Dict, List, Set, Any
from dataclasses import dataclass
from rich.console import Console
import logging
from pathlib import Path

@dataclass
class TaskContext:
    """Context for task execution"""
    task_id: str
    agent_assignments: Dict[str, str]
    dependencies: List[str]
    state: Dict[str, Any]
    priority: int = 1

class IntegrationOrchestrator:
    """Orchestrates integration between AI agents"""

    def __init__(self):
        self.console = Console()
        self.active_tasks: Dict[str, TaskContext] = {}
        self.agent_states: Dict[str, Dict] = {}
        self.execution_queue = asyncio.Queue()

    async def delegate_task(self, task: Dict) -> str:
        """Delegate task to appropriate agents"""
        context = await self._create_task_context(task)
        self.active_tasks[context.task_id] = context

        # Queue task for execution
        await self.execution_queue.put(context)
        return context.task_id

    async def _create_task_context(self, task: Dict) -> TaskContext:
        """Create execution context for task"""
        # Analyze task requirements
        requirements = await self._analyze_requirements(task)

        # Assign agents based on specialties
        assignments = await self._assign_agents(requirements)

        return TaskContext(
            task_id=task["id"],
            agent_assignments=assignments,
            dependencies=requirements.get("dependencies", []),
            state={"status": "pending"}
        )

    async def _analyze_requirements(self, task: Dict) -> Dict:
        """Analyze task requirements"""
        requirements = {
            "shell_ops": task.get("shell_operations", False),
            "code_execution": task.get("code_execution", False),
            "routing": task.get("routing", False),
            "dependencies": task.get("dependencies", [])
        }

        return requirements

    async def _assign_agents(self, requirements: Dict) -> Dict[str, str]:
        """Assign agents to task components"""
        assignments = {}

        if requirements["shell_ops"]:
            assignments["shell"] = "tgpt"
        if requirements["code_execution"]:
            assignments["execution"] = "openinterpreter"
        if requirements["routing"]:
            assignments["routing"] = "lmstudio"

        return assignments

    async def execute_tasks(self):
        """Execute tasks in parallel"""
        while True:
            context = await self.execution_queue.get()

            try:
                # Execute task components in parallel
                execution_tasks = [
                    self._execute_component(agent, role, context)
                    for role, agent in context.agent_assignments.items()
                ]

                results = await asyncio.gather(*execution_tasks)

                # Update task state
                success = all(result.get("status") == "success" for result in results)
                self.active_tasks[context.task_id].state["status"] = \
                    "completed" if success else "failed"

            except Exception as e:
                logging.error(f"Task execution failed: {e}")
                self.active_tasks[context.task_id].state["status"] = "failed"
                self.active_tasks[context.task_id].state["error"] = str(e)

            finally:
                self.execution_queue.task_done()

    async def _execute_component(self,
                               agent: str,
                               role: str,
                               context: TaskContext) -> Dict:
        """Execute task component with specific agent"""
        try:
            # Get agent endpoint
            endpoint = self._get_agent_endpoint(agent)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint}/execute",
                    json={
                        "role": role,
                        "task_id": context.task_id,
                        "state": context.state
                    }
                ) as resp:
                    result = await resp.json()

                    # Update agent state
                    self.agent_states[agent] = result.get("agent_state", {})

                    return result

        except Exception as e:
            logging.error(f"Component execution failed: {e}")
            return {"status": "failed", "error": str(e)}

    def _get_agent_endpoint(self, agent: str) -> str:
        """Get agent endpoint URL"""
        ports = {
            "tgpt": 4891,
            "lmstudio": 1234,
            "openinterpreter": 8080
        }
        return f"http://localhost:{ports[agent]}"

async def main():
    """Main entry point"""
    orchestrator = IntegrationOrchestrator()
    console = Console()

    try:
        # Start task execution loop
        asyncio.create_task(orchestrator.execute_tasks())

        # Example task
        task = {
            "id": "task1",
            "shell_operations": True,
            "code_execution": True,
            "routing": True,
            "description": "Test integration"
        }

        task_id = await orchestrator.delegate_task(task)
        console.print(f"Task delegated with ID: {task_id}")

        # Wait for task completion
        while orchestrator.active_tasks[task_id].state["status"] == "pending":
            await asyncio.sleep(1)

        console.print(f"Task status: {orchestrator.active_tasks[task_id].state}")

    except Exception as e:
        console.print(f"[red]Error during orchestration: {e}")

if __name__ == "__main__":
    asyncio.run(main())
