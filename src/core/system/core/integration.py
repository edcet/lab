"""Integration Layer for Model Coordination

This module provides the core integration layer for coordinating multiple models.
Key components:
- ModelCapability: Defines model capabilities and characteristics
- ModelCoordinator: Orchestrates task execution across models
- ModelRegistry: Manages model registration and discovery
"""

import asyncio
import aiohttp
from typing import Dict, List, Any
from pathlib import Path
import json
import logging
from dataclasses import dataclass

@dataclass
class ModelCapability:
    """Defines the capabilities and parameters of a model"""
    name: str  # Model identifier
    endpoint: str  # API endpoint
    capabilities: List[str]  # Core capabilities
    specialties: List[str]  # Specialized capabilities
    context_window: int  # Maximum context length
    response_quality: float  # Quality metric (0-1)

class ModelCoordinator:
    """Coordinate operations between multiple models"""

    def __init__(self, config: Dict):
        self.config = config
        self.models = self._setup_models()
        self.active_models = set()
        self.task_history = []
        self.integration_points = {}

    def _setup_models(self) -> Dict[str, ModelCapability]:
        """Setup model capabilities"""
        return {
            "ollama": ModelCapability(
                name="ollama",
                endpoint="http://localhost:11434",
                capabilities=["code", "reasoning", "analysis"],
                specialties=["technical", "implementation"],
                context_window=8192,
                response_quality=0.9
            ),
            "tgpt": ModelCapability(
                name="tgpt",
                endpoint="http://localhost:4891",
                capabilities=["shell", "system", "automation"],
                specialties=["command", "workflow"],
                context_window=4096,
                response_quality=0.85
            ),
            "lmstudio": ModelCapability(
                name="lmstudio",
                endpoint="http://localhost:1234",
                capabilities=["analysis", "generation", "completion"],
                specialties=["creative", "exploration"],
                context_window=16384,
                response_quality=0.95
            )
        }

    async def coordinate_task(self, task: Dict) -> Dict:
        """Coordinate task execution across models"""
        # Analyze task requirements
        requirements = await self._analyze_requirements(task)

        # Select appropriate models
        selected_models = await self._select_models(requirements)

        # Design execution plan
        plan = await self._design_execution_plan(selected_models, task)

        # Execute plan
        result = await self._execute_plan(plan)

        # Store task history
        self.task_history.append({
            "task": task,
            "plan": plan,
            "result": result
        })

        return result

    async def _analyze_requirements(self, task: Dict) -> Dict:
        """Analyze task requirements"""
        requirements = {
            "capabilities": [],
            "context_size": 0,
            "quality_threshold": 0.0
        }

        # Extract required capabilities
        if "code" in task["type"]:
            requirements["capabilities"].extend(["code", "technical"])
        if "system" in task["type"]:
            requirements["capabilities"].extend(["shell", "automation"])
        if "creative" in task["type"]:
            requirements["capabilities"].extend(["generation", "exploration"])

        # Determine context size
        requirements["context_size"] = len(str(task["input"])) * 1.5

        # Set quality threshold
        requirements["quality_threshold"] = 0.8 if task["critical"] else 0.6

        return requirements

    async def _select_models(self, requirements: Dict) -> List[ModelCapability]:
        """Select appropriate models for task"""
        selected = []

        for model in self.models.values():
            # Check capability match
            if any(cap in model.capabilities for cap in requirements["capabilities"]):
                # Check context window
                if model.context_window >= requirements["context_size"]:
                    # Check quality threshold
                    if model.response_quality >= requirements["quality_threshold"]:
                        selected.append(model)

        return selected

    async def _design_execution_plan(self, models: List[ModelCapability], task: Dict) -> Dict:
        """Design parallel execution plan"""
        plan = {
            "stages": [],
            "dependencies": {},
            "fallbacks": {}
        }

        # Sort models by specialties
        specialists = self._sort_by_specialty(models, task["type"])

        # Design execution stages
        current_stage = []
        for model in specialists:
            stage_task = self._create_stage_task(model, task)
            current_stage.append(stage_task)

            # Add fallback if available
            fallback = self._find_fallback(model, specialists)
            if fallback:
                plan["fallbacks"][model.name] = fallback.name

        plan["stages"].append(current_stage)

        return plan

    async def _execute_plan(self, plan: Dict) -> Dict:
        """Execute parallel execution plan"""
        results = {}

        # Execute stages in sequence
        for stage in plan["stages"]:
            # Execute tasks in parallel
            stage_results = await asyncio.gather(*[
                self._execute_task(task) for task in stage
            ])

            # Store results
            for task, result in zip(stage, stage_results):
                results[task["model"]] = result

            # Check fallbacks
            for task in stage:
                if task["model"] in plan["fallbacks"]:
                    if not self._verify_result(results[task["model"]]):
                        # Execute fallback
                        fallback = plan["fallbacks"][task["model"]]
                        results[task["model"]] = await self._execute_fallback(
                            task,
                            self.models[fallback]
                        )

        return self._combine_results(results)

    async def _execute_task(self, task: Dict) -> Dict:
        """Execute single task"""
        model = self.models[task["model"]]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{model.endpoint}/v1/completions",
                    json=task["input"]
                ) as resp:
                    return await resp.json()
        except Exception as e:
            logging.error(f"Task execution failed: {e}")
            return None

    def _sort_by_specialty(self, models: List[ModelCapability], task_type: str) -> List[ModelCapability]:
        """Sort models by specialty match"""
        return sorted(
            models,
            key=lambda m: len(set(m.specialties) & set(task_type.split())),
            reverse=True
        )

    def _create_stage_task(self, model: ModelCapability, task: Dict) -> Dict:
        """Create task for specific model"""
        return {
            "model": model.name,
            "input": self._adapt_input(task["input"], model),
            "timeout": 30
        }

    def _adapt_input(self, input_data: Any, model: ModelCapability) -> Dict:
        """Adapt input for specific model"""
        return {
            "prompt": input_data,
            "max_tokens": model.context_window,
            "temperature": 0.7,
            "top_p": 0.9
        }

    def _verify_result(self, result: Dict) -> bool:
        """Verify task result"""
        return result is not None and "choices" in result

    async def _execute_fallback(self, task: Dict, model: ModelCapability) -> Dict:
        """Execute fallback task"""
        fallback_task = self._create_stage_task(model, task)
        return await self._execute_task(fallback_task)

    def _combine_results(self, results: Dict) -> Dict:
        """Combine results from multiple models"""
        valid_results = {
            k: v for k, v in results.items()
            if self._verify_result(v)
        }

        if not valid_results:
            return None

        # Combine text from all valid results
        combined_text = "\n".join([
            r["choices"][0]["text"]
            for r in valid_results.values()
        ])

        return {
            "text": combined_text,
            "sources": list(valid_results.keys())
        }

class ModelRegistry:
    """Registry for managing available models

    Responsibilities:
    - Track available models and their capabilities
    - Monitor model health and availability
    - Provide model discovery and filtering
    """

    def __init__(self):
        self.models = {}  # name -> ModelCapability mapping
        self.active_models = set()  # Set of available model names

    async def register_model(self, capability: ModelCapability):
        """Register new model"""
        self.models[capability.name] = capability

        # Test model availability
        if await self._test_model(capability):
            self.active_models.add(capability.name)

    async def _test_model(self, model: ModelCapability) -> bool:
        """Test if model is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{model.endpoint}/health"
                ) as resp:
                    return resp.status == 200
        except:
            return False

    def get_active_models(self) -> List[ModelCapability]:
        """Get list of active models"""
        return [
            self.models[name]
            for name in self.active_models
        ]

    def find_models_by_capability(self, capability: str) -> List[ModelCapability]:
        """Find models with specific capability"""
        return [
            model for model in self.models.values()
            if capability in model.capabilities
            and model.name in self.active_models
        ]

    def find_models_by_specialty(self, specialty: str) -> List[ModelCapability]:
        """Find models with specific specialty"""
        return [
            model for model in self.models.values()
            if specialty in model.specialties
            and model.name in self.active_models
        ]
