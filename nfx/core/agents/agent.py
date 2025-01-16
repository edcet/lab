"""NFX Agent Module

Advanced agent implementation with autonomous operation capabilities,
continuous execution, and interactive feedback.
"""

import asyncio
import enum
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from uuid import uuid4

from ..compute.engine import ComputeEngine
from ..memory.manager import MemoryManager
from ..neural.llm_interface import LLMInterface
from .tool_integration import ToolIntegration, ToolType, ToolResponse

logger = logging.getLogger(__name__)

@dataclass
class TaskPlan:
    """Task execution plan"""
    steps: List[str]
    tools: List[str]
    expected_outcomes: List[str]
    constraints: List[str]
    created_at: datetime = None
    performance_metrics: Dict[str, float] = None
    execution_history: List[Dict[str, Any]] = None

@dataclass
class AgentConfig:
    """Agent configuration"""
    name: str
    role: str
    goals: List[str]
    constraints: List[str]
    resources: List[str]
    memory_size: int = 10000
    max_iterations: int = 100
    continuous_mode: bool = False
    continuous_limit: Optional[int] = None
    autonomous_mode: bool = False
    tool_selection: bool = True
    self_improvement: bool = True
    learning_rate: float = 0.1
    performance_threshold: float = 0.8
    evolution_enabled: bool = True

@dataclass
class AgentState:
    """Agent state representation"""
    agent_id: str
    config: AgentConfig
    memory: Dict[str, Any]
    capabilities: Set[str]
    current_task: Optional[str] = None
    current_plan: Optional[TaskPlan] = None
    status: str = "idle"
    created_at: datetime = None
    last_active: datetime = None
    performance_history: List[Dict[str, float]] = None
    evolution_state: Dict[str, Any] = None
    tool_usage_stats: Dict[str, Dict[str, float]] = None

class UserFeedback(str, enum.Enum):
    """User feedback options"""
    CONTINUE = "CONTINUE"
    MODIFY = "MODIFY"
    STOP = "STOP"
    EXIT = "EXIT"

class Agent:
    """NFX Agent implementation with AutoGPT capabilities"""

    def __init__(
        self,
        config: AgentConfig,
        compute_engine: ComputeEngine,
        memory_manager: MemoryManager,
        llm_interface: LLMInterface,
    ):
        self.config = config
        self.compute = compute_engine
        self.memory = memory_manager
        self.llm = llm_interface
        self.tool_integration = ToolIntegration()

        # Initialize state with enhanced tracking
        self.state = AgentState(
            agent_id=str(uuid4()),
            config=config,
            memory={},
            capabilities=set(),
            created_at=datetime.now(),
            last_active=datetime.now(),
            performance_history=[],
            evolution_state={
                "generation": 0,
                "improvements": [],
                "learning_curve": []
            },
            tool_usage_stats={}
        )

        # Set up logging
        self.logger = logging.getLogger(f"agent.{self.state.agent_id}")

    async def start(self):
        """Start agent execution"""
        self.logger.info(f"Starting agent {self.config.name}")

        # Initialize tool integration
        await self.tool_integration.initialize()

        self.state.status = "running"

        try:
            iteration = 0
            while self._should_continue(iteration):
                # Update state
                self.state.last_active = datetime.now()
                iteration += 1

                if self.config.autonomous_mode:
                    # Autonomous execution
                    await self._autonomous_execution_cycle()
                else:
                    # Standard execution
                    action = await self._get_next_action()
                    if not action:
                        break

                    result = await self._execute_action(action)
                    await self._process_result(result)

                    if not self.config.continuous_mode:
                        feedback = await self._get_user_feedback()
                        if feedback == UserFeedback.STOP:
                            break
                        elif feedback == UserFeedback.EXIT:
                            raise KeyboardInterrupt

        except KeyboardInterrupt:
            self.logger.info("Agent execution interrupted by user")
            self.state.status = "interrupted"
        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            self.state.status = "failed"
        else:
            self.state.status = "completed"

        await self._cleanup()

    async def _autonomous_execution_cycle(self):
        """Execute one autonomous cycle with enhanced monitoring"""
        cycle_start = datetime.now()
        cycle_metrics = {"start_time": cycle_start}

        try:
            # Plan next task if none active
            if not self.state.current_task:
                task = await self._plan_next_task()
                if task:
                    self.state.current_task = task
                    plan = await self._create_task_plan(task)
                    if plan:
                        self.state.current_plan = plan
                        cycle_metrics["planning_time"] = (datetime.now() - cycle_start).total_seconds()

            # Execute current plan
            if self.state.current_plan:
                execution_start = datetime.now()
                completed = await self._execute_task_plan(self.state.current_plan)
                cycle_metrics["execution_time"] = (datetime.now() - execution_start).total_seconds()

                if completed:
                    # Update performance metrics
                    cycle_metrics["success"] = True
                    cycle_metrics["completion_time"] = (datetime.now() - cycle_start).total_seconds()

                    # Store execution history
                    if not self.state.current_plan.execution_history:
                        self.state.current_plan.execution_history = []
                    self.state.current_plan.execution_history.append(cycle_metrics)

                    # Clear state
                    self.state.current_task = None
                    self.state.current_plan = None

                    # Self-improvement if enabled and needed
                    if self.config.self_improvement:
                        improvement_needed = await self._evaluate_performance(cycle_metrics)
                        if improvement_needed:
                            await self._improve_capabilities()

        except Exception as e:
            cycle_metrics["success"] = False
            cycle_metrics["error"] = str(e)
            self.logger.error(f"Autonomous cycle failed: {e}")

        finally:
            # Update performance history
            self.state.performance_history.append(cycle_metrics)
            # Update last active timestamp
            self.state.last_active = datetime.now()

    async def _plan_next_task(self) -> Optional[str]:
        """Plan next task with enhanced context awareness"""
        context = {
            "goals": self.config.goals,
            "constraints": self.config.constraints,
            "capabilities": self.state.capabilities,
            "memory": self.state.memory,
            "performance_history": self.state.performance_history[-10:],  # Last 10 cycles
            "tool_usage_stats": self.state.tool_usage_stats
        }

        try:
            response = await self.llm.plan_task(context)
            if response and isinstance(response, str):
                return response
        except Exception as e:
            self.logger.error(f"Task planning failed: {e}")
        return None

    async def _create_task_plan(self, task: str) -> Optional[TaskPlan]:
        """Create execution plan with performance tracking"""
        try:
            # Get plan from LLM with enhanced context
            plan_data = await self.llm.create_plan(
                task=task,
                capabilities=self.state.capabilities,
                constraints=self.config.constraints,
                performance_history=self.state.performance_history[-5:],  # Last 5 cycles
                tool_usage_stats=self.state.tool_usage_stats
            )

            if not plan_data:
                return None

            return TaskPlan(
                steps=plan_data.get("steps", []),
                tools=plan_data.get("tools", []),
                expected_outcomes=plan_data.get("expected_outcomes", []),
                constraints=plan_data.get("constraints", []),
                created_at=datetime.now(),
                performance_metrics={},
                execution_history=[]
            )

        except Exception as e:
            self.logger.error(f"Plan creation failed: {e}")
            return None

    async def _execute_task_plan(self, plan: TaskPlan) -> bool:
        """Execute task plan with performance monitoring"""
        start_time = datetime.now()
        step_results = []

        try:
            for i, step in enumerate(plan.steps):
                step_start = datetime.now()
                step_metrics = {"step": i, "start_time": step_start}

                # Select appropriate tool
                tool = None
                if self.config.tool_selection:
                    tool = await self._select_tool(step, plan.tools)
                    if tool:
                        step_metrics["selected_tool"] = tool

                # Execute step
                result = await self._execute_step(step, tool)
                step_metrics["success"] = result.get("success", False)
                step_metrics["execution_time"] = (datetime.now() - step_start).total_seconds()

                if not result.get("success"):
                    plan.performance_metrics = self._calculate_performance_metrics(step_results)
                    return False

                # Update tool usage statistics
                if tool:
                    self._update_tool_stats(tool, step_metrics)

                # Store step result
                step_results.append({
                    "step": step,
                    "tool": tool,
                    "result": result,
                    "metrics": step_metrics
                })

                # Update memory with enhanced context
                self.state.memory[f"step_{datetime.now().isoformat()}"] = {
                    "step": step,
                    "tool": tool,
                    "result": result,
                    "metrics": step_metrics,
                    "context": {
                        "plan_progress": f"{i + 1}/{len(plan.steps)}",
                        "performance": step_metrics
                    }
                }

            # Calculate and store final performance metrics
            plan.performance_metrics = self._calculate_performance_metrics(step_results)
            return True

        except Exception as e:
            self.logger.error(f"Plan execution failed: {e}")
            plan.performance_metrics = self._calculate_performance_metrics(step_results)
            return False

    def _calculate_performance_metrics(self, step_results: List[Dict]) -> Dict[str, float]:
        """Calculate comprehensive performance metrics"""
        if not step_results:
            return {}

        total_time = sum(s["metrics"]["execution_time"] for s in step_results)
        success_rate = sum(1 for s in step_results if s["metrics"]["success"]) / len(step_results)

        tool_usage = {}
        for step in step_results:
            if tool := step.get("tool"):
                tool_usage[tool] = tool_usage.get(tool, 0) + 1

        return {
            "total_execution_time": total_time,
            "success_rate": success_rate,
            "steps_completed": len(step_results),
            "tool_usage": tool_usage
        }

    def _update_tool_stats(self, tool: str, metrics: Dict[str, Any]):
        """Update tool usage statistics"""
        if tool not in self.state.tool_usage_stats:
            self.state.tool_usage_stats[tool] = {
                "usage_count": 0,
                "success_count": 0,
                "total_time": 0,
                "average_time": 0
            }

        stats = self.state.tool_usage_stats[tool]
        stats["usage_count"] += 1
        if metrics.get("success"):
            stats["success_count"] += 1
        stats["total_time"] += metrics["execution_time"]
        stats["average_time"] = stats["total_time"] / stats["usage_count"]

    async def _evaluate_performance(self, metrics: Dict[str, Any]) -> bool:
        """Evaluate if performance improvement is needed"""
        if not metrics.get("success", False):
            return True

        # Calculate recent performance
        recent_cycles = self.state.performance_history[-5:]  # Last 5 cycles
        if not recent_cycles:
            return False

        success_rate = sum(1 for c in recent_cycles if c.get("success", False)) / len(recent_cycles)
        return success_rate < self.config.performance_threshold

    async def _improve_capabilities(self):
        """Improve agent capabilities through learning and evolution"""
        try:
            # Analyze recent performance
            performance = await self._analyze_performance()

            # Generate improvements
            improvements = await self.llm.generate_improvements(
                performance=performance,
                current_capabilities=self.state.capabilities,
                memory=self.state.memory,
                tool_usage_stats=self.state.tool_usage_stats
            )

            if improvements:
                # Apply improvements
                new_capabilities = set(improvements.get("new_capabilities", []))
                self.state.capabilities.update(new_capabilities)

                # Update evolution state
                self.state.evolution_state["generation"] += 1
                self.state.evolution_state["improvements"].append({
                    "timestamp": datetime.now().isoformat(),
                    "new_capabilities": list(new_capabilities),
                    "performance_snapshot": performance
                })

                # Update learning curve
                self.state.evolution_state["learning_curve"].append({
                    "generation": self.state.evolution_state["generation"],
                    "performance": performance.get("overall_score", 0),
                    "capabilities_count": len(self.state.capabilities)
                })

                self.logger.info(
                    f"Evolution {self.state.evolution_state['generation']}: "
                    f"Added capabilities: {new_capabilities}"
                )

        except Exception as e:
            self.logger.error(f"Self-improvement failed: {e}")

    async def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze agent's recent performance"""
        recent_history = self.state.performance_history[-10:]  # Last 10 cycles
        if not recent_history:
            return {}

        success_rate = sum(1 for c in recent_history if c.get("success", False)) / len(recent_history)
        avg_execution_time = sum(c.get("execution_time", 0) for c in recent_history) / len(recent_history)

        tool_performance = {}
        for tool, stats in self.state.tool_usage_stats.items():
            if stats["usage_count"] > 0:
                tool_performance[tool] = {
                    "success_rate": stats["success_count"] / stats["usage_count"],
                    "average_time": stats["average_time"]
                }

        return {
            "overall_score": success_rate,
            "execution_efficiency": 1.0 / avg_execution_time if avg_execution_time > 0 else 0,
            "tool_performance": tool_performance,
            "capabilities_count": len(self.state.capabilities),
            "memory_usage": len(self.state.memory),
            "evolution_generation": self.state.evolution_state["generation"]
        }

    def _should_continue(self, iteration: int) -> bool:
        """Check if agent should continue execution"""
        if self.state.status != "running":
            return False

        if iteration >= self.config.max_iterations:
            self.logger.info("Reached maximum iterations")
            return False

        if (
            self.config.continuous_mode
            and self.config.continuous_limit
            and iteration >= self.config.continuous_limit
        ):
            self.logger.info("Reached continuous execution limit")
            return False

        return True

    async def _get_next_action(self) -> Optional[Dict[str, Any]]:
        """Get next action from LLM"""
        try:
            # Prepare context
            context = {
                "name": self.config.name,
                "role": self.config.role,
                "goals": self.config.goals,
                "memory": self.state.memory,
                "current_task": self.state.current_task
            }

            # Get action from LLM
            response = await self.llm.get_next_action(context)

            # Validate response
            if not self._is_valid_action(response):
                self.logger.error(f"Invalid action response: {response}")
                return None

            return response

        except Exception as e:
            self.logger.error(f"Failed to get next action: {e}")
            return None

    def _is_valid_action(self, action: Dict[str, Any]) -> bool:
        """Validate action response"""
        required_fields = ["type", "input"]
        return all(field in action for field in required_fields)

    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action"""
        try:
            self.logger.info(f"Executing action: {action['type']}")

            # Execute based on action type
            if action["type"] == "process":
                result = await self.compute.process_data(action["input"])
            elif action["type"] == "memory":
                result = await self.memory.execute_operation(action["input"])
            elif action["type"] == "llm":
                result = await self.llm.process_input(action["input"])
            else:
                raise ValueError(f"Unknown action type: {action['type']}")

            return {
                "success": True,
                "result": result
            }

        except Exception as e:
            self.logger.error(f"Action execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _process_result(self, result: Dict[str, Any]):
        """Process action result"""
        # Update memory with result
        if result["success"]:
            memory_key = f"result_{datetime.now().isoformat()}"
            self.state.memory[memory_key] = result["result"]

        # Trim memory if needed
        if len(self.state.memory) > self.config.memory_size:
            oldest_key = min(self.state.memory.keys())
            del self.state.memory[oldest_key]

    async def _get_user_feedback(self) -> UserFeedback:
        """Get feedback from user"""
        while True:
            try:
                response = input(
                    "\nContinue agent execution? "
                    "[continue/modify/stop/exit]: "
                ).upper()

                if response in UserFeedback.__members__:
                    return UserFeedback[response]

                print("Invalid input. Please try again.")

            except EOFError:
                return UserFeedback.EXIT

    async def _cleanup(self):
        """Cleanup agent resources"""
        try:
            # Save final state
            self.state.last_active = datetime.now()

            # Cleanup compute resources
            await self.compute.cleanup()

            # Cleanup memory
            await self.memory.cleanup()

            # Cleanup LLM interface
            await self.llm.cleanup()

            # Cleanup tool integration
            await self.tool_integration.cleanup()

            self.logger.info("Agent cleanup completed")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")

    async def save_state(self, path: Path):
        """Save agent state to file"""
        try:
            state_dict = {
                "agent_id": self.state.agent_id,
                "config": self.config.__dict__,
                "memory": self.state.memory,
                "capabilities": list(self.state.capabilities),
                "current_task": self.state.current_task,
                "current_plan": self.state.current_plan.__dict__ if self.state.current_plan else None,
                "status": self.state.status,
                "created_at": self.state.created_at.isoformat(),
                "last_active": self.state.last_active.isoformat()
            }

            path.write_text(str(state_dict))
            self.logger.info(f"Agent state saved to {path}")

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            raise

    @classmethod
    async def load_state(
        cls,
        path: Path,
        compute_engine: ComputeEngine,
        memory_manager: MemoryManager,
        llm_interface: LLMInterface
    ) -> "Agent":
        """Load agent from saved state"""
        try:
            # Load state dict
            state_dict = eval(path.read_text())

            # Create config
            config = AgentConfig(**state_dict["config"])

            # Create agent
            agent = cls(config, compute_engine, memory_manager, llm_interface)

            # Restore state
            agent.state.agent_id = state_dict["agent_id"]
            agent.state.memory = state_dict["memory"]
            agent.state.capabilities = set(state_dict["capabilities"])
            agent.state.current_task = state_dict["current_task"]

            if state_dict["current_plan"]:
                agent.state.current_plan = TaskPlan(**state_dict["current_plan"])

            agent.state.status = state_dict["status"]
            agent.state.created_at = datetime.fromisoformat(state_dict["created_at"])
            agent.state.last_active = datetime.fromisoformat(state_dict["last_active"])

            return agent

        except Exception as e:
            logger.error(f"Failed to load agent state: {e}")
            raise

    async def _select_tool(self, step: str, available_tools: List[str]) -> Optional[str]:
        """Select best tool for step execution with enhanced capability matching"""
        try:
            # Extract required capabilities from step
            required_capabilities = await self.llm.extract_capabilities(step)

            # Get step context
            step_context = {
                "step": step,
                "required_capabilities": required_capabilities,
                "tool_stats": self.state.tool_usage_stats,
                "recent_performance": self.state.performance_history[-5:]  # Last 5 cycles
            }

            # Select tool with performance awareness
            selected_tool = await self.tool_integration.select_tool(
                input_text=step,
                required_capabilities=set(required_capabilities),
                context=step_context
            )

            if selected_tool and selected_tool.value in available_tools:
                return selected_tool.value

            return None

        except Exception as e:
            self.logger.error(f"Tool selection failed: {e}")
            return None

    async def _execute_step(self, step: str, tool: Optional[str] = None) -> Dict[str, Any]:
        """Execute a single step with enhanced error handling and telemetry"""
        start_time = datetime.now()
        metrics = {"start_time": start_time}

        try:
            if tool:
                # Execute with specific tool
                result = await self._execute_with_tool(step, tool)
                metrics["tool_used"] = tool
            else:
                # Execute with default compute engine
                result = await self.compute.process_data({
                    "step": step,
                    "context": self.state.memory,
                    "metrics": metrics
                })

            success = bool(result)
            metrics["success"] = success
            metrics["execution_time"] = (datetime.now() - start_time).total_seconds()

            return {
                "success": success,
                "result": result,
                "metrics": metrics
            }

        except Exception as e:
            self.logger.error(f"Step execution failed: {e}")
            metrics["success"] = False
            metrics["error"] = str(e)
            metrics["execution_time"] = (datetime.now() - start_time).total_seconds()

            return {
                "success": False,
                "error": str(e),
                "metrics": metrics
            }

    async def _execute_with_tool(self, step: str, tool: str) -> Any:
        """Execute step with specific tool and enhanced monitoring"""
        try:
            # Convert tool string to ToolType
            tool_type = ToolType(tool.lower())

            # Prepare execution context
            context = {
                "step": step,
                "tool_stats": self.state.tool_usage_stats.get(tool, {}),
                "recent_performance": self.state.performance_history[-3:]  # Last 3 cycles
            }

            # Execute with tool
            response = await self.tool_integration.execute_with_tool(
                tool_type=tool_type,
                input_text=step,
                context=context
            )

            if response:
                return response.text
            return None

        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return None
