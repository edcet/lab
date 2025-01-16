"""NFX Agent Protocol Module

Advanced agent protocol implementation with task management, step execution,
and artifact handling capabilities.
"""

import asyncio
import logging
import pathlib
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from dataclasses import dataclass
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ..compute.engine import ComputeEngine
from ..memory.manager import MemoryManager
from ..neural.llm_interface import LLMInterface

logger = logging.getLogger(__name__)

@dataclass
class Task:
    """Task representation"""
    task_id: str
    input: str
    additional_input: Optional[Dict[str, Any]] = None
    artifacts: List[str] = None
    status: str = "pending"
    created_at: datetime = None
    completed_at: datetime = None

@dataclass
class Step:
    """Step representation"""
    step_id: str
    task_id: str
    input: str
    status: str = "created"
    output: Optional[str] = None
    artifacts: List[str] = None
    created_at: datetime = None
    completed_at: datetime = None

class AgentProtocolServer:
    """NFX Agent Protocol Server"""

    def __init__(
        self,
        compute_engine: ComputeEngine,
        memory_manager: MemoryManager,
        llm_interface: LLMInterface,
    ):
        self.compute = compute_engine
        self.memory = memory_manager
        self.llm = llm_interface
        self.tasks: Dict[str, Task] = {}
        self.steps: Dict[str, List[Step]] = defaultdict(list)
        self.artifacts: Dict[str, bytes] = {}

    async def start(self, port: int = 8000, router: APIRouter = None):
        """Start the agent protocol server"""
        logger.info("Starting NFX Agent Protocol Server...")

        app = FastAPI(
            title="NFX Agent Protocol Server",
            description="Advanced agent protocol implementation with quantum capabilities",
            version="v1.0",
        )

        # Configure CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        if router:
            app.include_router(router, prefix="/api/v1")

        @app.get("/")
        async def root():
            return {"status": "running"}

        # Add routes
        @app.post("/tasks")
        async def create_task(input: str, additional_input: Optional[Dict[str, Any]] = None) -> Task:
            return await self.create_task(input, additional_input)

        @app.get("/tasks")
        async def list_tasks() -> List[Task]:
            return list(self.tasks.values())

        @app.get("/tasks/{task_id}")
        async def get_task(task_id: str) -> Task:
            return await self.get_task(task_id)

        @app.post("/tasks/{task_id}/steps")
        async def execute_step(task_id: str, input: str) -> Step:
            return await self.execute_step(task_id, input)

        @app.get("/tasks/{task_id}/steps")
        async def list_steps(task_id: str) -> List[Step]:
            return self.steps[task_id]

        # Start server
        config = {
            "bind": f"0.0.0.0:{port}",
            "workers": 4
        }

        logger.info(f"NFX Agent Protocol Server running on http://localhost:{port}")
        await asyncio.create_task(app.run(**config))

    async def create_task(self, input: str, additional_input: Optional[Dict[str, Any]] = None) -> Task:
        """Create a new task"""
        task_id = str(uuid4())
        task = Task(
            task_id=task_id,
            input=input,
            additional_input=additional_input,
            created_at=datetime.now(),
            artifacts=[],
            status="created"
        )
        self.tasks[task_id] = task
        logger.info(f"Created task {task_id}: {input}")
        return task

    async def get_task(self, task_id: str) -> Task:
        """Get task by ID"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        return self.tasks[task_id]

    async def execute_step(self, task_id: str, input: str) -> Step:
        """Execute a step for the given task"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        step_id = str(uuid4())
        step = Step(
            step_id=step_id,
            task_id=task_id,
            input=input,
            created_at=datetime.now(),
            artifacts=[],
            status="created"
        )
        self.steps[task_id].append(step)

        try:
            # Process step using LLM interface
            result = await self.llm.process_step(input)

            # Update step with result
            step.output = result
            step.status = "completed"
            step.completed_at = datetime.now()

            # Check if task is complete
            task = self.tasks[task_id]
            if self._is_task_complete(result):
                task.status = "completed"
                task.completed_at = datetime.now()

            logger.info(f"Executed step {step_id} for task {task_id}")
            return step

        except Exception as e:
            step.status = "failed"
            step.output = str(e)
            logger.error(f"Step {step_id} failed: {e}")
            raise

    def _is_task_complete(self, step_output: str) -> bool:
        """Check if task is complete based on step output"""
        return "TASK_COMPLETE" in step_output.upper()

    async def store_artifact(self, task_id: str, artifact_id: str, data: bytes):
        """Store an artifact for a task"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        self.artifacts[artifact_id] = data
        self.tasks[task_id].artifacts.append(artifact_id)

    async def get_artifact(self, artifact_id: str) -> StreamingResponse:
        """Get an artifact by ID"""
        if artifact_id not in self.artifacts:
            raise ValueError(f"Artifact {artifact_id} not found")

        return StreamingResponse(
            content=iter([self.artifacts[artifact_id]]),
            media_type="application/octet-stream"
        )
