"""Core Gateway Module for Model Orchestration"""

import asyncio
import json
import yaml
import hashlib
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import random

import aiohttp
import numpy as np
from cryptography.fernet import Fernet
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout

@dataclass
class ModelState:
    """Tracks the state of model interactions"""
    active_models: Dict[str, float]  # Model -> coherence mapping
    state_vector: List[float]  # State amplitudes
    interaction_history: List[Dict]
    coherence_threshold: float = 0.7
    health_status: Dict[str, bool] = None
    load_metrics: Dict[str, float] = None
    response_times: Dict[str, List[float]] = None

@dataclass
class RoutingConfig:
    """Configuration for request routing"""
    strategy: str = "adaptive"  # adaptive, round-robin, least-loaded
    health_check_interval: int = 30  # seconds
    max_retries: int = 3
    timeout: float = 10.0  # seconds
    circuit_breaker_threshold: int = 5
    load_balance_window: int = 100

class ModelGateway:
    """Core orchestration layer for model interactions"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(".config/ai/config.yml")
        self.config = None
        self.model_state = None
        self.routing_config = None
        self.backends = None
        self.circuit_breakers = None
        self.background_tasks = set()

    async def initialize(self):
        """Initialize the gateway with configuration and start background tasks."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"AI config not found at {self.config_path}")

        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)

        # Core component initialization
        self.model_state = ModelState(
            active_models={},
            state_vector=[],
            interaction_history=[],
            health_status={},
            load_metrics={},
            response_times={}
        )

        # Initialize routing config
        self.routing_config = RoutingConfig()

        # Define core backend interfaces from config
        self.backends = self.config.get("backends", {})
        if not self.backends:
            raise ValueError("No backend configurations found")

        # Initialize health monitoring
        self._initialize_health_monitoring()

        # Circuit breaker state
        self.circuit_breakers = {model: {"failures": 0, "last_failure": None}
                               for model in self.backends}

        # Start background tasks
        self._start_background_tasks()

    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        loop = asyncio.get_event_loop()
        self.background_tasks.add(
            loop.create_task(self._health_check_loop())
        )
        self.background_tasks.add(
            loop.create_task(self._load_balance_loop())
        )

    async def _health_check_loop(self):
        """Continuously monitor backend health"""
        while True:
            try:
                for backend, config in self.backends.items():
                    is_healthy = await self._check_backend_health(backend, config)
                    self.model_state.health_status[backend] = is_healthy

                    if not is_healthy:
                        self.circuit_breakers[backend]["failures"] += 1
                        self.circuit_breakers[backend]["last_failure"] = datetime.now()
                    else:
                        self.circuit_breakers[backend]["failures"] = 0

                await asyncio.sleep(self.routing_config.health_check_interval)
            except Exception as e:
                print(f"Health check error: {e}")
                await asyncio.sleep(5)  # Back off on error

    async def _load_balance_loop(self):
        """Monitor and adjust load balancing"""
        while True:
            try:
                for backend in self.backends:
                    # Calculate average response time
                    times = self.model_state.response_times.get(backend, [])
                    if times:
                        avg_time = sum(times[-self.routing_config.load_balance_window:]) / len(times)
                        self.model_state.load_metrics[backend] = avg_time

                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                print(f"Load balance error: {e}")
                await asyncio.sleep(5)

    async def _check_backend_health(self, backend: str, config: Dict) -> bool:
        """Check if a backend is healthy"""
        try:
            url = f"http://{config['host']}:{config['port']}/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=2) as response:
                    return response.status == 200
        except Exception:
            return False

    async def route_request(self, prompt: str, context: Dict = None) -> Dict:
        """Core routing interface with advanced routing strategies"""
        state_vector = self._calculate_state_vector(prompt)
        model_probabilities = self._calculate_model_probabilities(state_vector)

        # Get available models based on health and circuit breaker
        available_models = self._get_available_models()
        if not available_models:
            raise RuntimeError("No healthy models available")

        # Select models based on routing strategy
        selected_models = await self._select_models_with_strategy(
            available_models, model_probabilities
        )

        # Execute with retries and failover
        results = []
        for model in selected_models:
            for attempt in range(self.routing_config.max_retries):
                try:
                    start_time = datetime.now()
                    result = await self._execute_model(model, prompt, context)

                    # Record response time
                    duration = (datetime.now() - start_time).total_seconds()
                    if model not in self.model_state.response_times:
                        self.model_state.response_times[model] = []
                    self.model_state.response_times[model].append(duration)

                    results.append(result)
                    break
                except Exception as e:
                    if attempt == self.routing_config.max_retries - 1:
                        # Last attempt failed, try failover
                        failover_model = self._get_failover_model(model, available_models)
                        if failover_model:
                            result = await self._execute_model(failover_model, prompt, context)
                            results.append(result)
                        else:
                            raise RuntimeError(f"All retries failed for {model} and no failover available")

        return await self._combine_results(results)

    def _get_available_models(self) -> Set[str]:
        """Get list of available models based on health and circuit breaker"""
        available = set()
        for model in self.backends:
            # Check health status
            is_healthy = self.model_state.health_status.get(model, False)

            # Check circuit breaker
            circuit = self.circuit_breakers[model]
            is_open = circuit["failures"] >= self.routing_config.circuit_breaker_threshold

            if is_healthy and not is_open:
                available.add(model)

        return available

    async def _select_models_with_strategy(
        self, available_models: Set[str], probabilities: Dict[str, float]
    ) -> List[str]:
        """Select models based on routing strategy"""
        if self.routing_config.strategy == "round-robin":
            return list(available_models)
        elif self.routing_config.strategy == "least-loaded":
            # Sort by load metrics
            return sorted(
                available_models,
                key=lambda m: self.model_state.load_metrics.get(m, float('inf'))
            )
        else:  # adaptive
            # Combine probabilities with health and load metrics
            scores = {}
            for model in available_models:
                prob = probabilities.get(model, 0)
                load = self.model_state.load_metrics.get(model, 1.0)
                health = float(self.model_state.health_status.get(model, False))
                scores[model] = prob * health / load

            return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def _get_failover_model(self, failed_model: str, available_models: Set[str]) -> Optional[str]:
        """Get a failover model when primary model fails"""
        available_models.discard(failed_model)
        if not available_models:
            return None

        # Select model with best health and load metrics
        scores = {}
        for model in available_models:
            load = self.model_state.load_metrics.get(model, 1.0)
            health = float(self.model_state.health_status.get(model, False))
            scores[model] = health / load

        return max(scores.items(), key=lambda x: x[1])[0] if scores else None

    async def _execute_model(self, model: str, prompt: str, context: Dict = None) -> Dict:
        """Execute request on specific model with monitoring"""
        config = self.backends[model]
        url = f"http://{config['host']}:{config['port']}/v1/completions"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"prompt": prompt, "context": context},
                timeout=self.routing_config.timeout
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Model {model} failed with status {response.status}")
                return await response.json()

    async def _combine_results(self, results: List[Dict]) -> Dict:
        """Combine results from multiple models with enhanced logic"""
        if not results:
            raise RuntimeError("No results to combine")

        # Combine completions with weights based on model coherence
        completions = []
        weights = []

        for result in results:
            model = result.get("model", "unknown")
            coherence = self.model_state.active_models.get(model, 0.5)
            completions.append(result.get("completion", ""))
            weights.append(coherence)

        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            weights = [1.0 / len(weights)] * len(weights)
        else:
            weights = [w / total_weight for w in weights]

        # Combine completions
        final_completion = ""
        for completion, weight in zip(completions, weights):
            final_completion += completion * weight

        return {
            "completion": final_completion,
            "model_weights": dict(zip([r.get("model", "unknown") for r in results], weights)),
            "timestamp": datetime.now().isoformat()
        }
