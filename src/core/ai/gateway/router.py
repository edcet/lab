"""AI Request Router

Production-ready implementation with load shedding, circuit breaking,
and advanced routing strategies.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import random
import asyncio
from datetime import datetime, timedelta
import logging

@dataclass
class RouterMetrics:
    """Metrics for routing decisions"""
    request_counts: Dict[str, int]
    error_counts: Dict[str, int]
    response_times: Dict[str, List[float]]
    last_used: Dict[str, datetime]
    load_metrics: Dict[str, float] = field(default_factory=dict)
    circuit_states: Dict[str, str] = field(default_factory=dict)

class RequestRouter:
    """Production-ready request router with advanced features"""

    def __init__(self):
        self.metrics = RouterMetrics(
            request_counts={},
            error_counts={},
            response_times={},
            last_used={},
            load_metrics={},
            circuit_states={}
        )
        self._current_round_robin_idx = 0
        self._load_shed_threshold = 0.9
        self._circuit_break_threshold = 5
        self._circuit_reset_interval = 300  # 5 minutes
        self._logger = logging.getLogger('gateway.router')

    async def route_request(self,
                          available_models: Set[str],
                          model_health: Dict[str, bool],
                          model_load: Dict[str, float],
                          required_capabilities: Optional[List[str]] = None,
                          strategy: str = "adaptive") -> Optional[str]:
        """Route a request using the specified strategy"""
        try:
            # Check load shedding
            if self._should_shed_load(model_load):
                raise RuntimeError("System overloaded, shedding load")

            # Filter out circuit-broken models
            available_models = self._filter_circuit_broken(available_models)
            if not available_models:
                raise RuntimeError("No available models after circuit breaker")

            # Route based on strategy
            if strategy == "adaptive":
                return await self.route_adaptive(
                    available_models,
                    model_health,
                    model_load,
                    required_capabilities
                )
            elif strategy == "round_robin":
                return self.route_round_robin(available_models)
            elif strategy == "least_loaded":
                return self.route_least_loaded(available_models, model_load)
            elif strategy == "weighted_random":
                return self.route_weighted_random(
                    available_models,
                    self._calculate_weights(available_models, model_load)
                )
            else:
                raise ValueError(f"Unknown routing strategy: {strategy}")

        except Exception as e:
            self._logger.error(f"Routing error: {e}")
            raise

    def _should_shed_load(self, model_load: Dict[str, float]) -> bool:
        """Determine if we should shed load"""
        return all(load > self._load_shed_threshold
                  for load in model_load.values())

    def _filter_circuit_broken(self, models: Set[str]) -> Set[str]:
        """Filter out circuit-broken models"""
        return {
            model for model in models
            if self.metrics.circuit_states.get(model) != "open"
        }

    async def route_adaptive(self,
                           available_models: Set[str],
                           model_health: Dict[str, bool],
                           model_load: Dict[str, float],
                           required_capabilities: Optional[List[str]] = None) -> str:
        """Enhanced adaptive routing with circuit breaking"""
        if not available_models:
            raise RuntimeError("No models available for routing")

        # Calculate scores with circuit breaker consideration
        model_scores = {}
        for model in available_models:
            # Skip unhealthy or circuit-broken models
            if not model_health.get(model, False):
                continue
            if self.metrics.circuit_states.get(model) == "open":
                continue

            # Base score starts with inverse of load
            base_score = 1 - model_load.get(model, 0)

            # Factor in error rate with time decay
            error_score = self._calculate_error_score(model)

            # Factor in response time with recent emphasis
            response_score = self._calculate_response_score(model)

            # Combine scores with weights
            model_scores[model] = (
                base_score * 0.4 +
                error_score * 0.3 +
                response_score * 0.3
            )

        if not model_scores:
            raise RuntimeError("No healthy models available")

        return max(model_scores.items(), key=lambda x: x[1])[0]

    def _calculate_error_score(self, model: str) -> float:
        """Calculate error score with time decay"""
        now = datetime.now()
        recent_window = timedelta(minutes=5)

        # Get recent errors
        recent_errors = sum(
            1 for time in self.metrics.error_counts.get(model, [])
            if now - time < recent_window
        )

        # Calculate error rate with time decay
        total_requests = self.metrics.request_counts.get(model, 0)
        if total_requests == 0:
            return 1.0

        error_rate = recent_errors / total_requests
        return 1 - error_rate

    def _calculate_response_score(self, model: str) -> float:
        """Calculate response score emphasizing recent performance"""
        times = self.metrics.response_times.get(model, [])
        if not times:
            return 0.5

        # Weight recent times more heavily
        weighted_sum = sum(
            time * (i + 1)
            for i, time in enumerate(times[-10:])
        )
        weights_sum = sum(i + 1 for i in range(len(times[-10:])))

        avg_time = weighted_sum / weights_sum
        return 1 / (1 + avg_time)

    def update_metrics(self,
                      model: str,
                      response_time: float,
                      error: bool = False) -> None:
        """Update routing metrics with circuit breaker logic"""
        # Initialize metrics for new models
        if model not in self.metrics.request_counts:
            self.metrics.request_counts[model] = 0
            self.metrics.error_counts[model] = 0
            self.metrics.response_times[model] = []
            self.metrics.circuit_states[model] = "closed"

        # Update counts
        self.metrics.request_counts[model] += 1
        if error:
            self.metrics.error_counts[model] += 1

            # Check circuit breaker
            if (self.metrics.error_counts[model] >=
                self._circuit_break_threshold):
                self._open_circuit(model)

        # Update response times (keep last 1000)
        self.metrics.response_times[model].append(response_time)
        if len(self.metrics.response_times[model]) > 1000:
            self.metrics.response_times[model].pop(0)

        # Update last used timestamp
        self.metrics.last_used[model] = datetime.now()

    def _open_circuit(self, model: str) -> None:
        """Open circuit breaker for a model"""
        self.metrics.circuit_states[model] = "open"
        self._logger.warning(f"Circuit breaker opened for model: {model}")

        # Schedule circuit reset
        asyncio.create_task(self._reset_circuit(model))

    async def _reset_circuit(self, model: str) -> None:
        """Reset circuit breaker after timeout"""
        await asyncio.sleep(self._circuit_reset_interval)

        if model in self.metrics.circuit_states:
            self.metrics.circuit_states[model] = "closed"
            self.metrics.error_counts[model] = 0
            self._logger.info(f"Circuit breaker reset for model: {model}")

    def get_model_metrics(self, model: str) -> Dict:
        """Get enhanced metrics for a model"""
        if model not in self.metrics.request_counts:
            return {
                "requests": 0,
                "errors": 0,
                "error_rate": 0.0,
                "avg_response_time": 0.0,
                "last_used": None,
                "circuit_state": "closed",
                "load": 0.0
            }

        requests = self.metrics.request_counts[model]
        errors = self.metrics.error_counts[model]
        error_rate = errors / requests if requests > 0 else 0.0

        response_times = self.metrics.response_times.get(model, [])
        avg_response_time = (
            sum(response_times) / len(response_times)
            if response_times else 0.0
        )

        return {
            "requests": requests,
            "errors": errors,
            "error_rate": error_rate,
            "avg_response_time": avg_response_time,
            "last_used": self.metrics.last_used.get(model),
            "circuit_state": self.metrics.circuit_states.get(model, "closed"),
            "load": self.metrics.load_metrics.get(model, 0.0)
        }
