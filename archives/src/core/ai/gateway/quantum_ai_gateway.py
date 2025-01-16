"""AI Gateway Router

Production-ready implementation with load balancing, circuit breaking,
and advanced routing strategies with pattern-based intelligence, bulletproof state management,
and evolutionary agent network.
"""

from typing import Dict, List, Optional, Set, AsyncIterator, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import random
import asyncio
from datetime import datetime, timedelta, timezone
import logging
from functools import lru_cache
from contextlib import asynccontextmanager, AsyncExitStack
import sqlite3
import aiosqlite
from pathlib import Path
import json
import aiohttp
import uuid
import importlib.util
import os
import websockets
import time
import statistics

class StateValidationError(Exception):
    """Raised when state validation fails"""
    pass

class ConcurrentModificationError(Exception):
    """Raised when concurrent modification is detected"""
    pass

class InvalidStateTransition(Exception):
    """Raised when state transition is invalid"""
    def __init__(self, component_id: str, current: Dict, attempted: Dict):
        self.component_id = component_id
        self.current = current
        self.attempted = attempted
        super().__init__(f"Invalid state transition for {component_id}")

@dataclass
class StateTransition:
    """Represents a state transition with validation"""
    component_id: str
    previous: Dict
    next: Dict
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict = field(default_factory=dict)

class StateStore:
    """Thread-safe state storage with history"""

    def __init__(self, max_history: int = 1000):
        self._state = {}
        self._history = defaultdict(list)
        self._max_history = max_history
        self._locks = defaultdict(asyncio.Lock)

    async def get(self, key: str) -> Dict:
        """Get current state for key"""
        async with self._locks[key]:
            return self._state.get(key, {})

    async def compare_and_set(self, key: str, version: int, new_state: Dict) -> bool:
        """Atomic compare and set operation"""
        async with self._locks[key]:
            current = self._state.get(key, {})
            current_version = current.get('_metadata', {}).get('version', 0)

            if version != current_version:
                raise ConcurrentModificationError(
                    f"Version mismatch: expected {version}, got {current_version}"
                )

            # Store history
            self._history[key].append(StateTransition(
                component_id=key,
                previous=current,
                next=new_state
            ))

            # Prune history if needed
            if len(self._history[key]) > self._max_history:
                self._history[key] = self._history[key][-self._max_history:]

            # Update state
            self._state[key] = new_state
            return True

    async def get_history(self, key: str, limit: int = None) -> List[StateTransition]:
        """Get state transition history"""
        async with self._locks[key]:
            history = self._history[key]
            if limit:
                history = history[-limit:]
            return history

class StateManager:
    """Bulletproof state manager with validation and concurrency control"""

    def __init__(self):
        self.state = StateStore(max_history=1000)
        self.locks = defaultdict(asyncio.Lock)
        self.subscribers = defaultdict(set)
        self.validation_rules = defaultdict(list)
        self._logger = logging.getLogger('state_manager')

    @asynccontextmanager
    async def state_lock(self, component_id: str):
        """Context manager for state locks"""
        async with self.locks[component_id]:
            yield

    async def update_state(self,
                          component_id: str,
                          updates: Dict[str, Any],
                          metadata: Dict[str, Any] = None) -> bool:
        """Update state with validation and conflict resolution"""
        async with self.state_lock(component_id):
            try:
                # Get current state
                current = await self.state.get(component_id)

                # Create new state
                new_state = {
                    **current,
                    **updates,
                    '_metadata': {
                        'timestamp': datetime.now(timezone.utc),
                        'version': current.get('_metadata', {}).get('version', 0) + 1,
                        **metadata or {}
                    }
                }

                # Validate state transition
                validation_results = await asyncio.gather(*[
                    rule(current, new_state)
                    for rule in self.validation_rules[component_id]
                ], return_exceptions=True)

                # Check for validation errors
                for result in validation_results:
                    if isinstance(result, Exception):
                        raise StateValidationError(f"Validation failed: {result}")
                    if not result:
                        raise InvalidStateTransition(
                            component_id=component_id,
                            current=current,
                            attempted=new_state
                        )

                # Store state with optimistic locking
                try:
                    await self.state.compare_and_set(
                        component_id,
                        current.get('_metadata', {}).get('version'),
                        new_state
                    )
                except ConcurrentModificationError:
                    self._logger.warning(
                        f"Concurrent modification detected for {component_id}, retrying"
                    )
                    # Handle conflict with exponential backoff
                    return await self._retry_update(component_id, updates, metadata)

                # Notify subscribers
                await self._notify_subscribers(component_id, new_state)

                return True

            except Exception as e:
                self._logger.error(f"State update failed for {component_id}: {e}")
                raise

    async def _retry_update(self,
                           component_id: str,
                           updates: Dict[str, Any],
                           metadata: Dict[str, Any] = None,
                           attempt: int = 0) -> bool:
        """Retry state update with exponential backoff"""
        max_attempts = 5
        if attempt >= max_attempts:
            raise RuntimeError(f"Failed to update state after {max_attempts} attempts")

        # Exponential backoff
        await asyncio.sleep(0.1 * (2 ** attempt))

        return await self.update_state(component_id, updates, metadata)

    async def _notify_subscribers(self, component_id: str, new_state: Dict):
        """Notify subscribers of state changes"""
        notification_tasks = []
        for subscriber in self.subscribers[component_id]:
            task = asyncio.create_task(subscriber(new_state))
            notification_tasks.append(task)

        # Wait for all notifications with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*notification_tasks, return_exceptions=True),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            self._logger.warning(
                f"Notification timeout for {component_id}"
            )

    def add_validation_rule(self,
                          component_id: str,
                          rule: Callable[[Dict, Dict], bool]):
        """Add state validation rule"""
        self.validation_rules[component_id].append(rule)

    def subscribe(self,
                 component_id: str,
                 callback: Callable[[Dict], None]):
        """Subscribe to state changes"""
        self.subscribers[component_id].add(callback)

    def unsubscribe(self,
                    component_id: str,
                    callback: Callable[[Dict], None]):
        """Unsubscribe from state changes"""
        self.subscribers[component_id].discard(callback)

@dataclass
class Pattern:
    """Pattern detected in routing behavior"""
    id: str
    type: str
    data: Dict
    significance: float
    timestamp: datetime
    requires_action: bool = False

class BehaviorAnalyzer:
    def __init__(self, min_sequence_length: int, max_gap: timedelta):
        self.min_sequence_length = min_sequence_length
        self.max_gap = max_gap
        self.sequence_buffer = []

    async def analyze(self, data: Dict) -> List[Pattern]:
        self.sequence_buffer.append(data)
        self._prune_old_sequences()
        return await self._find_patterns()

    def _prune_old_sequences(self):
        now = datetime.now()
        self.sequence_buffer = [
            s for s in self.sequence_buffer
            if now - s['timestamp'] <= self.max_gap
        ]

    async def _find_patterns(self) -> List[Pattern]:
        patterns = []
        if len(self.sequence_buffer) >= self.min_sequence_length:
            # Analyze for behavioral patterns
            patterns.extend(await self._analyze_sequences())
        return patterns

class PerformanceAnalyzer:
    def __init__(self, window_size: int, threshold: float):
        self.window_size = window_size
        self.threshold = threshold
        self.metrics_history = []

    async def analyze(self, data: Dict) -> List[Pattern]:
        self.metrics_history.append(data)
        if len(self.metrics_history) > self.window_size:
            self.metrics_history.pop(0)
        return await self._detect_anomalies()

    async def _detect_anomalies(self) -> List[Pattern]:
        patterns = []
        if len(self.metrics_history) == self.window_size:
            # Detect performance anomalies
            patterns.extend(await self._analyze_metrics())
        return patterns

class ErrorAnalyzer:
    def __init__(self, correlation_threshold: float, min_occurrences: int):
        self.correlation_threshold = correlation_threshold
        self.min_occurrences = min_occurrences
        self.error_history = defaultdict(list)

    async def analyze(self, data: Dict) -> List[Pattern]:
        if 'error' in data:
            self.error_history[data['error']].append(data)
        return await self._find_error_patterns()

    async def _find_error_patterns(self) -> List[Pattern]:
        patterns = []
        for error_type, occurrences in self.error_history.items():
            if len(occurrences) >= self.min_occurrences:
                patterns.extend(await self._analyze_error_sequence(error_type, occurrences))
        return patterns

class ResourceAnalyzer:
    def __init__(self, sampling_rate: float, alert_threshold: float):
        self.sampling_rate = sampling_rate
        self.alert_threshold = alert_threshold
        self.resource_metrics = defaultdict(list)

    async def analyze(self, data: Dict) -> List[Pattern]:
        if random.random() <= self.sampling_rate:
            for resource, value in data.get('resources', {}).items():
                self.resource_metrics[resource].append(value)
        return await self._check_resource_patterns()

    async def _check_resource_patterns(self) -> List[Pattern]:
        patterns = []
        for resource, metrics in self.resource_metrics.items():
            if await self._analyze_resource_usage(resource, metrics):
                patterns.append(Pattern(
                    id=f"resource_{resource}",
                    type="resource_constraint",
                    data={'resource': resource, 'metrics': metrics[-10:]},
                    significance=0.9,
                    timestamp=datetime.now(),
                    requires_action=True
                ))
        return patterns

class LRUCache:
    def __init__(self, maxsize: int):
        self.cache = {}
        self.maxsize = maxsize

    def get(self, key: str) -> Optional[Dict]:
        return self.cache.get(key)

    def put(self, key: str, value: Dict):
        if len(self.cache) >= self.maxsize:
            # Remove oldest item
            oldest = next(iter(self.cache))
            del self.cache[oldest]
        self.cache[key] = value

class PatternEngine:
    def __init__(self):
        self.pattern_store = LRUCache(maxsize=10000)
        self.analyzers = {
            'behavior': BehaviorAnalyzer(
                min_sequence_length=3,
                max_gap=timedelta(seconds=30)
            ),
            'performance': PerformanceAnalyzer(
                window_size=300,
                threshold=2.0
            ),
            'error': ErrorAnalyzer(
                correlation_threshold=0.7,
                min_occurrences=3
            ),
            'resource': ResourceAnalyzer(
                sampling_rate=1.0,
                alert_threshold=0.85
            )
        }

    async def process_stream(self, data_stream: AsyncIterator[Dict]):
        async for data in data_stream:
            # Run analyzers concurrently
            analysis_tasks = [
                analyzer.analyze(data)
                for analyzer in self.analyzers.values()
            ]

            results = await asyncio.gather(*analysis_tasks)

            # Correlate patterns across analyzers
            correlated = self._correlate_patterns(results)

            # Store significant patterns
            for pattern in correlated:
                if pattern.significance > 0.8:
                    await self._store_pattern(pattern)
                    if pattern.requires_action:
                        await self._trigger_action(pattern)

    def _correlate_patterns(self, analyzer_results: List[List[Pattern]]) -> List[Pattern]:
        # Flatten results
        all_patterns = [p for patterns in analyzer_results for p in patterns]

        # Group by timestamp proximity
        grouped = defaultdict(list)
        for pattern in all_patterns:
            key = pattern.timestamp.replace(microsecond=0)
            grouped[key].append(pattern)

        # Find correlations
        correlated = []
        for timestamp, patterns in grouped.items():
            if len(patterns) > 1:
                # Patterns occurring together may be related
                correlation = self._calculate_correlation(patterns)
                if correlation > 0.7:
                    correlated.append(Pattern(
                        id=f"correlated_{timestamp.isoformat()}",
                        type="correlation",
                        data={'patterns': [p.data for p in patterns]},
                        significance=correlation,
                        timestamp=timestamp,
                        requires_action=any(p.requires_action for p in patterns)
                    ))

        return correlated

    async def _store_pattern(self, pattern: Pattern):
        self.pattern_store.put(pattern.id, {
            'pattern': pattern,
            'timestamp': datetime.now()
        })

    async def _trigger_action(self, pattern: Pattern):
        # Implement action triggering based on pattern type
        pass

    def _calculate_correlation(self, patterns: List[Pattern]) -> float:
        # Simple correlation based on timestamp proximity and type
        return 0.8  # Placeholder

@dataclass
class RouterMetrics:
    """Metrics for routing decisions"""
    request_counts: Dict[str, int] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)
    response_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    last_used: Dict[str, datetime] = field(default_factory=dict)
    load_metrics: Dict[str, float] = field(default_factory=dict)
    circuit_states: Dict[str, str] = field(default_factory=dict)
    patterns: Dict[str, Pattern] = field(default_factory=dict)

class TaskRouter:
    """Production-ready task router with advanced features and pattern intelligence"""

    def __init__(self):
        self.metrics = RouterMetrics()
        self._current_round_robin_idx = 0
        self._load_shed_threshold = 0.9
        self._circuit_break_threshold = 5
        self._circuit_reset_interval = 300  # 5 minutes
        self._logger = logging.getLogger('gateway.router')
        self.pattern_engine = PatternEngine()
        self.state_manager = StateManager()

        # Add validation rules
        self.state_manager.add_validation_rule(
            'router',
            self._validate_router_state
        )
        self.state_manager.add_validation_rule(
            'metrics',
            self._validate_metrics_state
        )

    async def _validate_router_state(self, current: Dict, next_state: Dict) -> bool:
        """Validate router state transitions"""
        # Ensure critical fields are present
        required_fields = {'available_models', 'model_health', 'model_load'}
        if not all(field in next_state for field in required_fields):
            return False

        # Validate model health states
        if not all(isinstance(v, bool) for v in next_state['model_health'].values()):
            return False

        # Validate load values
        if not all(0 <= v <= 1 for v in next_state['model_load'].values()):
            return False

        return True

    async def _validate_metrics_state(self, current: Dict, next_state: Dict) -> bool:
        """Validate metrics state transitions"""
        # Ensure metrics only increase
        for model in next_state.get('request_counts', {}):
            if (current.get('request_counts', {}).get(model, 0) >
                next_state['request_counts'][model]):
                return False

        # Validate error counts
        for model in next_state.get('error_counts', {}):
            if (current.get('error_counts', {}).get(model, 0) >
                next_state['error_counts'][model]):
                return False

        return True

    async def _process_patterns(self, model: str, duration: float, error: bool):
        """Process patterns for model behavior"""
        data = {
            'model': model,
            'duration': duration,
            'error': error,
            'timestamp': datetime.now(),
            'resources': {
                'load': self.metrics.load_metrics.get(model, 0),
                'error_rate': self._calculate_error_rate(model),
                'response_score': self._calculate_response_score(model)
            }
        }

        # Create single-item stream for pattern engine
        async def data_stream():
            yield data

        await self.pattern_engine.process_stream(data_stream())

    def _calculate_error_rate(self, model: str) -> float:
        if model not in self.metrics.error_counts:
            return 0.0
        return self.metrics.error_counts[model] / max(1, self.metrics.request_counts.get(model, 0))

    async def route_task(self,
                        available_models: Set[str],
                        model_health: Dict[str, bool],
                        model_load: Dict[str, float],
                        required_capabilities: Optional[List[str]] = None,
                        strategy: str = "adaptive") -> Optional[str]:
        """Route a task using the specified strategy"""
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

    def route_round_robin(self, available_models: Set[str]) -> str:
        """Simple round-robin routing"""
        models = sorted(list(available_models))
        if not models:
            raise RuntimeError("No models available")

        self._current_round_robin_idx = (
            (self._current_round_robin_idx + 1) % len(models)
        )
        return models[self._current_round_robin_idx]

    def route_least_loaded(self,
                          available_models: Set[str],
                          model_load: Dict[str, float]) -> str:
        """Route to least loaded model"""
        if not available_models:
            raise RuntimeError("No models available")

        return min(
            available_models,
            key=lambda m: model_load.get(m, 0)
        )

    def route_weighted_random(self,
                            available_models: Set[str],
                            weights: Dict[str, float]) -> str:
        """Route randomly with weights"""
        if not available_models:
            raise RuntimeError("No models available")

        # Normalize weights for available models
        total = sum(weights.get(m, 0) for m in available_models)
        if total == 0:
            return random.choice(list(available_models))

        r = random.random() * total
        cumsum = 0
        for model in available_models:
            cumsum += weights.get(model, 0)
            if cumsum > r:
                return model

        return next(iter(available_models))

    def _calculate_weights(self,
                         models: Set[str],
                         model_load: Dict[str, float]) -> Dict[str, float]:
        """Calculate routing weights based on load"""
        weights = {}
        for model in models:
            # Inverse of load gives higher weight to less loaded models
            load = model_load.get(model, 0)
            weights[model] = 1 - load
        return weights

    def _calculate_error_score(self, model: str) -> float:
        """Calculate error score with time decay"""
        if model not in self.metrics.error_counts:
            return 1.0

        errors = self.metrics.error_counts[model]
        requests = self.metrics.request_counts.get(model, 1)
        error_rate = errors / requests

        # Apply time decay if we have last_used info
        if model in self.metrics.last_used:
            time_since_last = (datetime.now() - self.metrics.last_used[model]).total_seconds()
            decay_factor = 1 / (1 + time_since_last / 3600)  # 1-hour half-life
            error_rate *= decay_factor

        return 1 - min(error_rate, 1)

    def _calculate_response_score(self, model: str) -> float:
        """Calculate response time score with recent emphasis"""
        times = self.metrics.response_times.get(model, [])
        if not times:
            return 1.0

        # Calculate weighted average with more weight to recent times
        weights = [0.8 ** i for i in range(len(times))]
        avg_time = sum(t * w for t, w in zip(times, weights)) / sum(weights)

        # Convert to score (lower time = higher score)
        return 1 / (1 + avg_time)

    def record_request(self, model: str, duration: float, error: bool = False) -> None:
        """Record metrics for a request"""
        self.metrics.request_counts[model] = self.metrics.request_counts.get(model, 0) + 1
        self.metrics.last_used[model] = datetime.now()
        self.metrics.response_times[model].append(duration)

        # Keep only last 100 response times
        if len(self.metrics.response_times[model]) > 100:
            self.metrics.response_times[model] = self.metrics.response_times[model][-100:]

        if error:
            self.metrics.error_counts[model] = self.metrics.error_counts.get(model, 0) + 1
            if self.metrics.error_counts[model] >= self._circuit_break_threshold:
                self._open_circuit(model)

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

class EvolutionError(Exception):
    """Raised when agent evolution fails"""
    pass

@dataclass
class Context:
    """Rich context for agent evolution"""
    ide_states: List[Dict]
    repl_state: Dict
    conversation_history: List[Dict]
    patterns: List[Pattern] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

@dataclass
class Learning:
    """Represents a learning opportunity for agents"""
    id: str
    source: str
    pattern: Pattern
    significance: float
    applicability: Dict[str, float]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class Performance:
    """Agent performance metrics"""
    success_rate: float
    response_time: float
    error_rate: float
    adaptation_score: float
    learning_rate: float

    @property
    def needs_improvement(self) -> bool:
        return (self.success_rate < 0.95 or
                self.error_rate > 0.05 or
                self.adaptation_score < 0.8)

    def delta(self) -> Dict[str, float]:
        """Calculate performance delta"""
        return {
            'success_delta': self.success_rate - 0.95,
            'error_delta': 0.05 - self.error_rate,
            'adaptation_delta': self.adaptation_score - 0.8
        }

class RingBuffer:
    """Thread-safe ring buffer"""

    def __init__(self, maxsize: int):
        self.maxsize = maxsize
        self.buffer = []
        self._lock = asyncio.Lock()

    async def append(self, item: Any):
        async with self._lock:
            self.buffer.append(item)
            if len(self.buffer) > self.maxsize:
                self.buffer.pop(0)

    def recent(self, n: int) -> List[Any]:
        """Get n most recent items"""
        return self.buffer[-n:]

class Agent:
    """Evolvable agent with performance tracking"""

    def __init__(self, agent_id: str, capabilities: Set[str]):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.performance_history = RingBuffer(maxsize=1000)
        self.evolution_history = RingBuffer(maxsize=100)
        self.state = {}

    @asynccontextmanager
    async def evolving(self):
        """Context manager for safe evolution"""
        checkpoint = self.state.copy()
        try:
            yield self
        except Exception as e:
            self.state = checkpoint
            raise EvolutionError(f"Evolution failed: {e}")

    def enhance(self, evolution_plan: Dict):
        """Apply evolution plan to agent"""
        for enhancement in evolution_plan['enhancements']:
            capability = enhancement['capability']
            updates = enhancement['updates']

            if capability in self.capabilities:
                self.state[capability] = {
                    **self.state.get(capability, {}),
                    **updates
                }
            else:
                self.capabilities.add(capability)
                self.state[capability] = updates

    async def analyze_performance(self) -> Performance:
        """Analyze recent performance"""
        history = self.performance_history.recent(100)

        if not history:
            return Performance(
                success_rate=1.0,
                response_time=0.0,
                error_rate=0.0,
                adaptation_score=1.0,
                learning_rate=1.0
            )

        successes = sum(1 for p in history if p['success'])
        total_time = sum(p['duration'] for p in history)
        errors = sum(1 for p in history if p['error'])

        return Performance(
            success_rate=successes / len(history),
            response_time=total_time / len(history),
            error_rate=errors / len(history),
            adaptation_score=self._calculate_adaptation_score(history),
            learning_rate=self._calculate_learning_rate(history)
        )

    def _calculate_adaptation_score(self, history: List[Dict]) -> float:
        """Calculate how well agent adapts to new situations"""
        if len(history) < 2:
            return 1.0

        # Calculate trend in performance
        success_trend = [h['success'] for h in history]
        return sum(success_trend[-10:]) / 10

    def _calculate_learning_rate(self, history: List[Dict]) -> float:
        """Calculate agent's learning rate"""
        if len(history) < 10:
            return 1.0

        # Compare recent vs older performance
        recent = history[-10:]
        older = history[-20:-10]

        recent_success = sum(1 for p in recent if p['success'])
        older_success = sum(1 for p in older if p['success'])

        return (recent_success - older_success) / 10 + 1

class AgentNetwork:
    """Network of evolvable agents with context awareness"""

    def __init__(self):
        self.agents = {}
        self.conversation_buffer = RingBuffer(maxsize=10000)
        self.pattern_engine = PatternEngine()
        self.state_manager = StateManager()

    async def capture_context(self) -> Context:
        """Capture rich execution context"""
        # Get current router state
        router_state = await self.state_manager.state.get('router')

        # Get recent patterns
        patterns = [
            p['pattern'] for p in
            self.pattern_engine.pattern_store.cache.values()
        ]

        return Context(
            ide_states=[router_state],
            repl_state={},  # To be implemented
            conversation_history=self.conversation_buffer.recent(100),
            patterns=patterns
        )

    async def evolve_agent(self, agent_id: str, context: Context):
        """Evolve agent based on context and performance"""
        agent = self.agents[agent_id]

        # Analyze agent's recent performance
        performance = await agent.analyze_performance()

        # Extract learning opportunities from context
        learnings = await self._extract_learnings(context)

        if performance.needs_improvement and learnings:
            # Generate targeted evolution plan
            evolution_plan = await self._generate_evolution_plan(
                agent=agent,
                performance=performance,
                learnings=learnings
            )

            # Apply evolution with rollback capability
            async with agent.evolving() as evolved_agent:
                evolved_agent.enhance(evolution_plan)

                # Validate evolution
                if not await self._validate_evolution(evolved_agent):
                    raise EvolutionError("Evolution validation failed")

            # Record successful evolution
            await self._record_evolution(
                agent_id=agent_id,
                plan=evolution_plan,
                results=performance.delta()
            )

    async def _extract_learnings(self, context: Context) -> List[Learning]:
        """Extract learning opportunities from context"""
        learnings = []

        # Learn from patterns
        for pattern in context.patterns:
            if pattern.significance > 0.8:
                learnings.append(Learning(
                    id=f"pattern_{pattern.id}",
                    source="pattern_engine",
                    pattern=pattern,
                    significance=pattern.significance,
                    applicability=self._calculate_applicability(pattern)
                ))

        # Learn from conversation history
        conv_patterns = await self.pattern_engine.analyze_conversations(
            context.conversation_history
        )
        for pattern in conv_patterns:
            learnings.append(Learning(
                id=f"conversation_{pattern.id}",
                source="conversation",
                pattern=pattern,
                significance=pattern.significance,
                applicability=self._calculate_applicability(pattern)
            ))

        return learnings

    def _calculate_applicability(self, pattern: Pattern) -> Dict[str, float]:
        """Calculate pattern applicability to different agent types"""
        applicability = {}
        for agent_id, agent in self.agents.items():
            score = sum(1 for cap in pattern.data.get('capabilities', [])
                       if cap in agent.capabilities)
            applicability[agent_id] = score / max(1, len(agent.capabilities))
        return applicability

    async def _generate_evolution_plan(self,
                                     agent: Agent,
                                     performance: Performance,
                                     learnings: List[Learning]) -> Dict:
        """Generate targeted evolution plan"""
        # Filter relevant learnings
        relevant = [l for l in learnings
                   if l.applicability[agent.agent_id] > 0.7]

        # Group by capability
        by_capability = defaultdict(list)
        for learning in relevant:
            caps = learning.pattern.data.get('capabilities', [])
            for cap in caps:
                by_capability[cap].append(learning)

        # Generate enhancement plan
        return {
            'agent_id': agent.agent_id,
            'performance': performance.delta(),
            'enhancements': [
                {
                    'capability': cap,
                    'updates': self._generate_capability_updates(learnings)
                }
                for cap, learnings in by_capability.items()
            ]
        }

    def _generate_capability_updates(self, learnings: List[Learning]) -> Dict:
        """Generate specific updates for a capability"""
        updates = {}
        for learning in learnings:
            pattern_data = learning.pattern.data
            if 'parameters' in pattern_data:
                updates['parameters'] = {
                    **updates.get('parameters', {}),
                    **pattern_data['parameters']
                }
            if 'rules' in pattern_data:
                updates['rules'] = [
                    *updates.get('rules', []),
                    *pattern_data['rules']
                ]
        return updates

    async def _validate_evolution(self, agent: Agent) -> bool:
        """Validate evolved agent"""
        # Validate capability consistency
        for capability, state in agent.state.items():
            if capability not in agent.capabilities:
                return False

            # Validate capability-specific rules
            if not await self._validate_capability(capability, state):
                return False

        return True

    async def _validate_capability(self, capability: str, state: Dict) -> bool:
        """Validate capability-specific state"""
        # Implement capability-specific validation
        return True

    async def _record_evolution(self,
                              agent_id: str,
                              plan: Dict,
                              results: Dict):
        """Record successful evolution"""
        evolution_record = {
            'agent_id': agent_id,
            'timestamp': datetime.now(timezone.utc),
            'plan': plan,
            'results': results
        }

        await self.agents[agent_id].evolution_history.append(evolution_record)

        # Update state manager
        await self.state_manager.update_state(
            f"agent_{agent_id}_evolution",
            evolution_record
        )

@dataclass
class IDEState:
    """State captured from IDE bridges"""
    code_context: Dict
    chat_history: List[Dict]
    terminal_state: Dict
    command_history: List[str]
    file_changes: List[Dict]
    project_context: Dict
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class ExponentialBackoff:
    """Exponential backoff for reconnection attempts"""

    def __init__(self, initial: float, maximum: float):
        self.initial = initial
        self.maximum = maximum
        self.current = initial

    def next(self) -> float:
        """Get next backoff delay"""
        delay = min(self.current, self.maximum)
        self.current = min(self.current * 2, self.maximum)
        return delay

    def reset(self):
        """Reset to initial delay"""
        self.current = self.initial

@dataclass
class IDEContext:
    """Rich IDE context with file and interaction history"""
    file_context: Dict
    edit_history: List[Dict]
    nav_history: List[Dict]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict = field(default_factory=dict)

class WebSocketError(Exception):
    """Raised when WebSocket operations fail"""
    pass

class IDEBridge:
    """Bridge to IDE with robust WebSocket connection"""

    def __init__(self, port: int):
        self.port = port
        self.websocket: Optional[WebSocket] = None
        self.reconnect_delay = ExponentialBackoff(
            initial=1.0,
            maximum=30.0
        )
        self._lock = asyncio.Lock()
        self._context_cache = LRUCache(maxsize=100)

    async def connect(self):
        """Establish WebSocket connection with retry"""
        while True:
            try:
                self.websocket = await websockets.connect(
                    f"ws://localhost:{self.port}/ai"
                )
                self.reconnect_delay.reset()
                break
            except ConnectionError:
                delay = self.reconnect_delay.next()
                logging.warning(
                    f"IDE connection failed, retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)

    async def get_context(self) -> IDEContext:
        """Get current IDE context with caching"""
        cache_key = f"context_{int(time.time() / 30)}"  # 30s cache
        if cached := self._context_cache.get(cache_key):
            return cached

        async with self._lock:
            if not self.websocket:
                await self.connect()

            try:
                # Get current file context
                file_context = await self._get_file_context()

                # Get recent edits
                edit_history = await self._get_edit_history()

                # Get navigation history
                nav_history = await self._get_navigation_history()

                context = IDEContext(
                    file_context=file_context,
                    edit_history=edit_history,
                    nav_history=nav_history
                )

                # Cache result
                self._context_cache.put(cache_key, context)
                return context

            except (WebSocketError, ConnectionError) as e:
                self.websocket = None
                raise WebSocketError(f"Failed to get IDE context: {e}")

    async def _get_file_context(self) -> Dict:
        """Get current file context"""
        try:
            await self.websocket.send(json.dumps({
                'type': 'get_file_context',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }))

            response = await asyncio.wait_for(
                self.websocket.recv(),
                            timeout=5.0
            )

            return json.loads(response)

                except Exception as e:
            raise WebSocketError(f"Failed to get file context: {e}")

    async def _get_edit_history(self) -> List[Dict]:
        """Get recent edit history"""
        try:
            await self.websocket.send(json.dumps({
                'type': 'get_edit_history',
                'limit': 100,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }))

            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=5.0
            )

            return json.loads(response)

        except Exception as e:
            raise WebSocketError(f"Failed to get edit history: {e}")

    async def _get_navigation_history(self) -> List[Dict]:
        """Get recent navigation history"""
        try:
            await self.websocket.send(json.dumps({
                'type': 'get_navigation_history',
                'limit': 50,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }))

            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=5.0
            )

            return json.loads(response)

        except Exception as e:
            raise WebSocketError(f"Failed to get navigation history: {e}")

    async def notify_adaptation(self, adaptation: Dict):
        """Notify IDE of system adaptation"""
        if not self.websocket:
            await self.connect()

        try:
            await self.websocket.send(json.dumps({
                'type': 'adaptation_notification',
                'adaptation': adaptation,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }))

        except Exception as e:
            logging.error(f"Failed to notify IDE of adaptation: {e}")
            self.websocket = None

class LLMNode:
    """Intelligent LLM endpoint with specialization"""

    def __init__(self, endpoint: str, specialties: List[str]):
        self.endpoint = endpoint
        self.specialties = set(specialties)
        self.performance_history = RingBuffer(maxsize=1000)
        self.state = {
            'health': True,
            'load': 0.0,
            'error_rate': 0.0,
            'specialization_scores': {s: 1.0 for s in specialties}
        }

    async def handle_request(self, request: Dict) -> Dict:
        """Handle LLM request with specialization awareness"""
        start_time = datetime.now()
        try:
            response = await self._send_request(request)
            duration = (datetime.now() - start_time).total_seconds()

            # Record success
            await self.performance_history.append({
                'timestamp': start_time,
                'duration': duration,
                'success': True,
                'specialties_used': [s for s in self.specialties
                                   if s in request.get('capabilities', [])]
            })

            return response

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()

            # Record failure
            await self.performance_history.append({
                'timestamp': start_time,
                'duration': duration,
                'success': False,
                'error': str(e),
                'specialties_used': [s for s in self.specialties
                                   if s in request.get('capabilities', [])]
            })
            raise

    async def _send_request(self, request: Dict) -> Dict:
        """Send request to LLM endpoint"""
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{self.endpoint}/v1/completions",
                                  json=request) as response:
                if response.status != 200:
                    raise RuntimeError(f"LLM request failed: {response.status}")
                return await response.json()

    def get_specialty_score(self, specialty: str) -> float:
        """Get effectiveness score for specialty"""
        if specialty not in self.specialties:
            return 0.0

        recent = self.performance_history.recent(100)
        if not recent:
            return 1.0

        # Calculate success rate for specialty
        specialty_requests = [r for r in recent
                            if specialty in r.get('specialties_used', [])]
        if not specialty_requests:
            return 1.0

        successes = sum(1 for r in specialty_requests if r['success'])
        return successes / len(specialty_requests)

class LLMNetwork:
    """Adaptive network of specialized LLM nodes"""

    def __init__(self):
        self.nodes = {
            'ollama': LLMNode('localhost:11434',
                             specialties=['code_verification', 'refactoring']),
            'lmstudio': LLMNode('localhost:1234',
                               specialties=['architecture', 'planning']),
            'tgpt': LLMNode('localhost:4891',
                           specialties=['documentation', 'shell'])
        }
        self.routing_history = RingBuffer(maxsize=10000)

    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        stats = {}
        for name, node in self.nodes.items():
            stats[name] = {
                'request_count': len(node.performance_history.buffer),
                'success_rate': self._calculate_success_rate(node),
                'specialty_scores': {
                    specialty: node.get_specialty_score(specialty)
                    for specialty in node.specialties
                }
            }
        return stats

    def _calculate_success_rate(self, node: LLMNode) -> float:
        """Calculate overall success rate for node"""
        recent = node.performance_history.recent(100)
        if not recent:
            return 1.0
        successes = sum(1 for r in recent if r['success'])
        return successes / len(recent)

    async def optimize_routing(self, effectiveness: Dict):
        """Optimize routing based on effectiveness patterns"""
        for node_name, metrics in effectiveness.items():
            if node_name in self.nodes:
                node = self.nodes[node_name]

                # Update specialization scores
                for specialty, score in metrics.get('specialty_scores', {}).items():
                    if specialty in node.specialties:
                        node.state['specialization_scores'][specialty] = score

                # Record routing optimization
                await self.routing_history.append({
                    'timestamp': datetime.now(timezone.utc),
                    'node': node_name,
                    'metrics': metrics,
                    'specialization_scores': node.state['specialization_scores'].copy()
                })

class SQLiteStorage:
    """Persistent storage for pattern learning"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure required tables exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    data JSON NOT NULL,
                    significance REAL NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS adaptations (
                    id TEXT PRIMARY KEY,
                    patterns_applied JSON NOT NULL,
                    system_state JSON NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            """)

    async def store_pattern(self, pattern: Pattern):
        """Store pattern in database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO patterns
                (id, type, data, significance, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                pattern.id,
                pattern.type,
                json.dumps(pattern.data),
                pattern.significance,
                pattern.timestamp.isoformat()
            ))
            await db.commit()

    async def get_patterns(self,
                          pattern_type: Optional[str] = None,
                          min_significance: float = 0.0,
                          limit: int = 1000) -> List[Pattern]:
        """Retrieve patterns from database"""
        async with aiosqlite.connect(self.db_path) as db:
            if pattern_type:
                cursor = await db.execute("""
                    SELECT * FROM patterns
                    WHERE type = ? AND significance >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (pattern_type, min_significance, limit))
        else:
                cursor = await db.execute("""
                    SELECT * FROM patterns
                    WHERE significance >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (min_significance, limit))

            rows = await cursor.fetchall()
            return [
                Pattern(
                    id=row[0],
                    type=row[1],
                    data=json.loads(row[2]),
                    significance=row[3],
                    timestamp=datetime.fromisoformat(row[4])
                )
                for row in rows
            ]

class SystemNervousSystem:
    """Central nervous system for adaptive AI operations"""

    def __init__(self):
        # IDE bridges for real interaction capture
        self.bridges = {
            'cursor': IDEBridge(port=9123),
            'warp': IDEBridge(port=9124),
            'windsurf': IDEBridge(port=9125)
        }

        # LLM routing based on actual effectiveness
        self.llm_network = LLMNetwork()

        # Real-time pattern learning
        self.pattern_engine = PatternEngine(
            storage=SQLiteStorage('patterns.db'),
            analyzers={
                'code': CodePatternAnalyzer(min_occurrences=3),
                'command': ShellPatternAnalyzer(min_confidence=0.8),
                'tool': ToolUsageAnalyzer(window_size=timedelta(hours=24))
            }
        )

        # Zellij session manager for persistent state
        self.zellij = ZellijManager(
            layout_file='~/.config/zellij/ai_layout.kdl',
            panes=['repl', 'logs', 'metrics']
        )

    async def learn_from_reality(self):
        """Learn from real system interactions"""
        # Capture real IDE interactions
        ide_states = await asyncio.gather(*[
            bridge.capture_state()
            for bridge in self.bridges.values()
        ])

        # Get terminal state
        terminal_state = await self.zellij.capture_state()

        # Extract patterns from real usage
        patterns = await self.pattern_engine.analyze({
            'ide_states': ide_states,
            'terminal_state': terminal_state,
            'llm_usage': self.llm_network.get_usage_stats()
        })

        if patterns.significant_changes_detected:
            # Adapt the system based on real patterns
            await self.adapt_to_patterns(patterns)

    async def adapt_to_patterns(self, patterns):
        """Adapt system behavior based on learned patterns"""
        # Adapt LLM routing based on effectiveness
        await self.llm_network.optimize_routing(patterns.llm_effectiveness)

        # Update IDE bridges based on usage patterns
        for bridge in self.bridges.values():
            await bridge.adapt(patterns.ide_patterns)

        # Evolve shell environment
        await self.zellij.evolve_layout(patterns.terminal_patterns)

        # Record adaptations for future learning
        await self.pattern_engine.record_adaptation({
            'timestamp': datetime.now(timezone.utc),
            'patterns_applied': patterns.to_dict(),
            'system_state': await self.capture_system_state()
        })

    async def capture_system_state(self) -> Dict:
        """Capture complete system state"""
        return {
            'ide_states': {
                name: await bridge.capture_state()
                for name, bridge in self.bridges.items()
            },
            'llm_network': self.llm_network.get_usage_stats(),
            'terminal_state': await self.zellij.capture_state(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

@dataclass
class Event:
    """System event with rich context"""
    id: str
    type: str
    source: str
    timestamp: datetime
    session_id: str
    data: Dict
    pane: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

@dataclass
class Analysis:
    """Pattern analysis result"""
    patterns: List[Pattern]
    confidence: float
    context: Dict
    metadata: Dict = field(default_factory=dict)

@dataclass
class Patterns:
    """Collection of related patterns"""
    items: List[Pattern]
    significance_score: float
    requires_adaptation: bool
    metadata: Dict = field(default_factory=dict)

class TimescaleDB:
    """Time-series optimized pattern storage"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure TimescaleDB schema exists"""
        with sqlite3.connect(self.db_path) as conn:
            # Create hypertable for time-series data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_events (
                    time TIMESTAMPTZ NOT NULL,
                    pattern_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    data JSONB NOT NULL,
                    metadata JSONB
                );

                SELECT create_hypertable('pattern_events', 'time');

                CREATE INDEX IF NOT EXISTS idx_pattern_events_pattern_id
                ON pattern_events (pattern_id, time DESC);

                CREATE INDEX IF NOT EXISTS idx_pattern_events_type_source
                ON pattern_events (event_type, source, time DESC);
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_correlations (
                    time TIMESTAMPTZ NOT NULL,
                    pattern_group TEXT NOT NULL,
                    patterns JSONB NOT NULL,
                    significance REAL NOT NULL,
                    metadata JSONB
                );

                SELECT create_hypertable('pattern_correlations', 'time');

                CREATE INDEX IF NOT EXISTS idx_pattern_correlations_group
                ON pattern_correlations (pattern_group, time DESC);
            """)

    async def store_event(self, event: Event, pattern: Pattern):
        """Store pattern event with time-series optimization"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO pattern_events (
                    time, pattern_id, event_type, source, data, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp.isoformat(),
                pattern.id,
                event.type,
                event.source,
                json.dumps(event.data),
                json.dumps(event.metadata)
            ))
            await db.commit()

    async def store_correlation(self,
                              timestamp: datetime,
                              pattern_group: str,
                              patterns: Patterns):
        """Store pattern correlation"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO pattern_correlations (
                    time, pattern_group, patterns, significance, metadata
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                timestamp.isoformat(),
                pattern_group,
                json.dumps([p.__dict__ for p in patterns.items]),
                patterns.significance_score,
                json.dumps(patterns.metadata)
            ))
            await db.commit()

    async def get_recent_patterns(self,
                                window: timedelta,
                                pattern_type: Optional[str] = None,
                                source: Optional[str] = None) -> List[Pattern]:
        """Get recent patterns with time-series optimization"""
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT DISTINCT ON (pattern_id)
                    pattern_id, data, metadata
                FROM pattern_events
                WHERE time >= ?
            """
            params = [
                (datetime.now(timezone.utc) - window).isoformat()
            ]

            if pattern_type:
                query += " AND event_type = ?"
                params.append(pattern_type)
            if source:
                query += " AND source = ?"
                params.append(source)

            query += " ORDER BY pattern_id, time DESC"

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            return [
                Pattern(
                    id=row[0],
                    type=json.loads(row[1])['type'],
                    data=json.loads(row[1]),
                    significance=json.loads(row[1])['significance'],
                    timestamp=datetime.fromisoformat(
                        json.loads(row[2])['timestamp']
                    )
                )
                for row in rows
            ]

class ShellAnalyzer:
    """Analyzes shell command patterns"""

    def __init__(self,
                 command_threshold: int,
                 sequence_length: int,
                 time_window: timedelta):
        self.command_threshold = command_threshold
        self.sequence_length = sequence_length
        self.time_window = time_window
        self.command_sequences = defaultdict(list)

    def can_handle(self, event_type: str) -> bool:
        return event_type in {'shell_command', 'command_output'}

    async def analyze(self, event: Event, context: Context) -> Analysis:
        if event.type == 'shell_command':
            return await self._analyze_command(event, context)
        else:
            return await self._analyze_output(event, context)

    async def _analyze_command(self, event: Event, context: Context) -> Analysis:
        # Track command sequence
        self.command_sequences[event.session_id].append({
            'command': event.data['command'],
            'timestamp': event.timestamp
        })

        # Prune old sequences
        self._prune_sequences(event.session_id)

        # Find command patterns
        patterns = []
        sequence = self.command_sequences[event.session_id]

        if len(sequence) >= self.sequence_length:
            # Look for repeated command sequences
            pattern = self._find_command_pattern(sequence)
            if pattern:
                patterns.append(pattern)

            # Check for command relationships
            relationships = self._find_command_relationships(sequence)
            patterns.extend(relationships)

        return Analysis(
            patterns=patterns,
            confidence=self._calculate_confidence(patterns),
            context={'sequence': sequence[-self.sequence_length:]}
        )

    def _prune_sequences(self, session_id: str):
        """Remove old commands from sequence"""
        cutoff = datetime.now(timezone.utc) - self.time_window
        self.command_sequences[session_id] = [
            cmd for cmd in self.command_sequences[session_id]
            if cmd['timestamp'] > cutoff
        ]

    def _find_command_pattern(self, sequence: List[Dict]) -> Optional[Pattern]:
        # Count command occurrences
        counts = Counter(cmd['command'] for cmd in sequence)

        # Find frequent commands
        frequent = [
            cmd for cmd, count in counts.items()
            if count >= self.command_threshold
        ]

        if frequent:
            return Pattern(
                id=f"shell_command_{hash(frequent[0])}",
                type="command_frequency",
                data={
                    'command': frequent[0],
                    'count': counts[frequent[0]],
                    'context': self._extract_command_context(sequence, frequent[0])
                },
                significance=counts[frequent[0]] / len(sequence),
                timestamp=datetime.now(timezone.utc)
            )
        return None

    def _find_command_relationships(self, sequence: List[Dict]) -> List[Pattern]:
        patterns = []

        # Look for command pairs that occur together
        for i in range(len(sequence) - 1):
            cmd1 = sequence[i]['command']
            cmd2 = sequence[i + 1]['command']

            # Check if this is a frequent pair
            pair_count = sum(
                1 for j in range(len(sequence) - 1)
                if sequence[j]['command'] == cmd1 and
                sequence[j + 1]['command'] == cmd2
            )

            if pair_count >= self.command_threshold:
                patterns.append(Pattern(
                    id=f"shell_sequence_{hash(cmd1 + cmd2)}",
                    type="command_sequence",
                    data={
                        'commands': [cmd1, cmd2],
                        'count': pair_count,
                        'time_gap': self._average_time_gap(sequence, cmd1, cmd2)
                    },
                    significance=pair_count / (len(sequence) - 1),
                    timestamp=datetime.now(timezone.utc)
                ))

        return patterns

    def _average_time_gap(self,
                         sequence: List[Dict],
                         cmd1: str,
                         cmd2: str) -> float:
        gaps = []
        for i in range(len(sequence) - 1):
            if (sequence[i]['command'] == cmd1 and
                sequence[i + 1]['command'] == cmd2):
                gap = (sequence[i + 1]['timestamp'] -
                      sequence[i]['timestamp']).total_seconds()
                gaps.append(gap)
        return sum(gaps) / len(gaps) if gaps else 0

class IDEAnalyzer:
    """Analyzes IDE interaction patterns"""

    def __init__(self,
                 file_patterns: bool = True,
                 navigation_patterns: bool = True,
                 edit_sequences: bool = True,
                 min_confidence: float = 0.85):
        self.analyze_files = file_patterns
        self.analyze_navigation = navigation_patterns
        self.analyze_edits = edit_sequences
        self.min_confidence = min_confidence
        self.interaction_history = defaultdict(list)

    def can_handle(self, event_type: str) -> bool:
        return event_type.startswith('ide_')

    async def analyze(self, event: Event, context: Context) -> Analysis:
        # Record interaction
        self.interaction_history[event.session_id].append({
            'type': event.type,
            'data': event.data,
            'timestamp': event.timestamp
        })

        patterns = []

        # Analyze based on enabled features
        if self.analyze_files:
            file_patterns = self._analyze_file_patterns(
                self.interaction_history[event.session_id]
            )
            patterns.extend(file_patterns)

        if self.analyze_navigation:
            nav_patterns = self._analyze_navigation(
                self.interaction_history[event.session_id]
            )
            patterns.extend(nav_patterns)

        if self.analyze_edits:
            edit_patterns = await self._analyze_edit_sequences(
                self.interaction_history[event.session_id],
                context
            )
            patterns.extend(edit_patterns)

        return Analysis(
            patterns=patterns,
            confidence=self._calculate_confidence(patterns),
            context={'recent_interactions': self.interaction_history[event.session_id][-50:]}
        )

    def _analyze_file_patterns(self, history: List[Dict]) -> List[Pattern]:
        patterns = []

        # Track file access frequency
        file_counts = Counter(
            i['data']['file']
            for i in history
            if 'file' in i['data']
        )

        # Find frequently accessed files
        for file, count in file_counts.most_common(5):
            if count >= 3:  # Minimum frequency threshold
                patterns.append(Pattern(
                    id=f"file_access_{hash(file)}",
                    type="file_frequency",
                    data={
                        'file': file,
                        'count': count,
                        'operations': self._get_file_operations(history, file)
                    },
                    significance=count / len(history),
                    timestamp=datetime.now(timezone.utc)
                ))

        return patterns

    def _analyze_navigation(self, history: List[Dict]) -> List[Pattern]:
        patterns = []

        # Track navigation sequences
        nav_sequences = [
            (h1['data']['from'], h1['data']['to'])
            for h1, h2 in zip(history[:-1], history[1:])
            if h1['type'] == 'ide_navigation' and
            h2['type'] == 'ide_navigation'
        ]

        # Find common navigation paths
        path_counts = Counter(nav_sequences)
        for path, count in path_counts.most_common(3):
            if count >= 2:  # Minimum sequence threshold
                patterns.append(Pattern(
                    id=f"navigation_{hash(str(path))}",
                    type="navigation_sequence",
                    data={
                        'path': path,
                        'count': count,
                        'context': self._get_navigation_context(history, path)
                    },
                    significance=count / len(nav_sequences) if nav_sequences else 0,
                    timestamp=datetime.now(timezone.utc)
                ))

        return patterns

    async def _analyze_edit_sequences(self,
                                    history: List[Dict],
                                    context: Context) -> List[Pattern]:
        patterns = []

        # Group edits by file
        file_edits = defaultdict(list)
        for interaction in history:
            if interaction['type'] == 'ide_edit':
                file = interaction['data']['file']
                file_edits[file].append(interaction)

        # Analyze edit patterns for each file
        for file, edits in file_edits.items():
            if len(edits) >= 3:  # Minimum edit sequence length
                edit_pattern = await self._find_edit_pattern(edits, context)
                if edit_pattern:
                    patterns.append(edit_pattern)

        return patterns

    async def _find_edit_pattern(self,
                                edits: List[Dict],
                                context: Context) -> Optional[Pattern]:
        # Calculate edit characteristics
        edit_sizes = [len(edit['data']['change']) for edit in edits]
        edit_locations = [edit['data']['location'] for edit in edits]
        time_gaps = [
            (edits[i + 1]['timestamp'] - edits[i]['timestamp']).total_seconds()
            for i in range(len(edits) - 1)
        ]

        # Look for patterns in edit behavior
        if self._is_systematic_editing(edit_sizes, edit_locations, time_gaps):
            return Pattern(
                id=f"edit_sequence_{hash(str(edits[0]['data']['file']))}",
                type="systematic_edits",
                data={
                    'file': edits[0]['data']['file'],
                    'edit_count': len(edits),
                    'average_size': sum(edit_sizes) / len(edit_sizes),
                    'location_pattern': self._describe_location_pattern(edit_locations),
                    'timing_pattern': self._describe_timing_pattern(time_gaps)
                },
                significance=self._calculate_edit_significance(
                    edit_sizes, edit_locations, time_gaps
                ),
                timestamp=datetime.now(timezone.utc)
            )
        return None

    def _is_systematic_editing(self,
                             sizes: List[int],
                             locations: List[Dict],
                             time_gaps: List[float]) -> bool:
        # Check for consistent edit sizes
        size_variance = statistics.variance(sizes) if len(sizes) > 1 else 0
        if size_variance < 10:  # Low variance indicates systematic edits
            return True

        # Check for sequential locations
        if self._is_sequential_locations(locations):
            return True

        # Check for consistent timing
        if time_gaps:
            time_variance = statistics.variance(time_gaps)
            if time_variance < 2:  # Consistent timing between edits
                return True

        return False

    def _calculate_confidence(self, patterns: List[Pattern]) -> float:
        if not patterns:
            return 0.0

        # Weight patterns by significance
        weighted_sum = sum(p.significance for p in patterns)
        return weighted_sum / len(patterns)

class LLMAnalyzer:
    """Analyzes LLM interaction patterns"""

    def __init__(self,
                 success_threshold: float = 0.8,
                 response_time_weight: float = 0.3,
                 accuracy_weight: float = 0.7):
        self.success_threshold = success_threshold
        self.response_time_weight = response_time_weight
        self.accuracy_weight = accuracy_weight
        self.interaction_history = defaultdict(list)

    def can_handle(self, event_type: str) -> bool:
        return event_type.startswith('llm_')

    async def analyze(self, event: Event, context: Context) -> Analysis:
        # Record interaction
        self.interaction_history[event.session_id].append({
            'type': event.type,
            'data': event.data,
            'timestamp': event.timestamp
        })

        patterns = []

        # Analyze LLM performance
        performance_patterns = self._analyze_performance(
            self.interaction_history[event.session_id]
        )
        patterns.extend(performance_patterns)

        # Analyze response patterns
        response_patterns = await self._analyze_responses(
            self.interaction_history[event.session_id],
            context
        )
        patterns.extend(response_patterns)

        return Analysis(
            patterns=patterns,
            confidence=self._calculate_confidence(patterns),
            context={'recent_interactions': self.interaction_history[event.session_id][-50:]}
        )

    def _analyze_performance(self, history: List[Dict]) -> List[Pattern]:
        patterns = []

        # Calculate performance metrics
        success_rate = self._calculate_success_rate(history)
        response_times = self._calculate_response_times(history)

        if success_rate < self.success_threshold:
            patterns.append(Pattern(
                id=f"llm_performance_{hash(str(history[-1]['timestamp']))}",
                type="performance_issue",
                data={
                    'success_rate': success_rate,
                    'avg_response_time': statistics.mean(response_times),
                    'error_types': self._get_error_types(history)
                },
                significance=1.0 - success_rate,
                timestamp=datetime.now(timezone.utc),
                requires_adaptation=True
            ))

        return patterns

    async def _analyze_responses(self,
                               history: List[Dict],
                               context: Context) -> List[Pattern]:
        patterns = []

        # Group responses by type
        response_groups = defaultdict(list)
        for interaction in history:
            if interaction['type'] == 'llm_response':
                response_type = self._classify_response(interaction['data'])
                response_groups[response_type].append(interaction)

        # Analyze each response type
        for response_type, responses in response_groups.items():
            if len(responses) >= 3:
                pattern = await self._find_response_pattern(
                    responses, response_type, context
                )
                if pattern:
                    patterns.append(pattern)

        return patterns

    def _calculate_success_rate(self, history: List[Dict]) -> float:
        responses = [h for h in history if h['type'] == 'llm_response']
        if not responses:
            return 1.0

        successes = sum(1 for r in responses if not r['data'].get('error'))
        return successes / len(responses)

    def _calculate_response_times(self, history: List[Dict]) -> List[float]:
        times = []
        for i in range(len(history) - 1):
            if (history[i]['type'] == 'llm_request' and
                history[i + 1]['type'] == 'llm_response'):
                duration = (history[i + 1]['timestamp'] -
                          history[i]['timestamp']).total_seconds()
                times.append(duration)
        return times or [0.0]

    def _get_error_types(self, history: List[Dict]) -> Dict[str, int]:
        error_counts = Counter()
        for h in history:
            if h['type'] == 'llm_response' and 'error' in h['data']:
                error_counts[h['data']['error']] += 1
        return dict(error_counts)

    def _classify_response(self, response_data: Dict) -> str:
        # Implement response classification logic
        if 'code' in response_data:
            return 'code_generation'
        elif 'explanation' in response_data:
            return 'explanation'
        elif 'error' in response_data:
            return 'error'
        return 'other'

    async def _find_response_pattern(self,
                                   responses: List[Dict],
                                   response_type: str,
                                   context: Context) -> Optional[Pattern]:
        # Calculate response characteristics
        response_sizes = [len(str(r['data'])) for r in responses]
        response_times = self._calculate_response_times(responses)

        # Look for patterns in response behavior
        if self._is_consistent_response_pattern(response_sizes, response_times):
            return Pattern(
                id=f"llm_response_{response_type}_{hash(str(responses[0]['timestamp']))}",
                type="response_pattern",
                data={
                    'response_type': response_type,
                    'count': len(responses),
                    'avg_size': statistics.mean(response_sizes),
                    'avg_time': statistics.mean(response_times),
                    'consistency': self._calculate_consistency(response_sizes, response_times)
                },
                significance=self._calculate_pattern_significance(
                    response_sizes, response_times
                ),
                timestamp=datetime.now(timezone.utc)
            )
        return None

    def _calculate_consistency(self,
                             sizes: List[int],
                             times: List[float]) -> float:
        # Calculate coefficient of variation (lower is more consistent)
        size_cv = statistics.stdev(sizes) / statistics.mean(sizes)
        time_cv = statistics.stdev(times) / statistics.mean(times)

        # Combine metrics with weights
        return 1.0 - (
            self.response_time_weight * time_cv +
            self.accuracy_weight * size_cv
        )

@dataclass
class SystemEvent:
    """Rich system event with context"""
    id: str
    type: str
    source: str
    timestamp: datetime
    data: Dict
    context: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)

@dataclass
class Adaptation:
    """System adaptation plan"""
    target: str
    changes: Dict
    rollback_plan: Dict
    dependencies: List[str] = field(default_factory=list)
    validation: Dict = field(default_factory=dict)

class AdaptivePatternNetwork:
    """Advanced pattern network with adaptation capabilities"""

    def __init__(self):
        # Core pattern storage with time-series optimization
        self.pattern_store = TimescaleDB(
            host='localhost',
            retention_period=timedelta(days=30)
        )

        # Real-time pattern detection engines
        self.detectors = {
            'shell': ShellPatternDetector(
                min_sequence_length=3,
                max_gap=timedelta(minutes=5),
                confidence_threshold=0.85
            ),
            'ide': IDEPatternDetector(
                editors=['cursor', 'warp', 'windsurf'],
                tracking={
                    'navigation': True,
                    'edits': True,
                    'commands': True,
                    'file_access': True
                }
            ),
            'llm': LLMPatternDetector(
                endpoints=['ollama', 'lmstudio', 'tgpt'],
                metrics=['latency', 'success_rate', 'token_efficiency']
            )
        }

        # Zellij session manager for persistent state
        self.session_manager = ZellijManager(
            layout='~/.config/zellij/ai_enhanced.kdl',
            panes={
                'repl': REPLPane(history_size=10000),
                'pattern_viz': PatternVisualizationPane(),
                'metrics': MetricsPane(update_interval=1.0)
            }
        )

        # State management
        self.state_manager = StateManager()
        self._setup_state_validation()

    def _setup_state_validation(self):
        """Setup state validation rules"""
        # Add validation for pattern detection
        self.state_manager.add_validation_rule(
            'pattern_detection',
            self._validate_pattern_detection
        )

        # Add validation for adaptations
        self.state_manager.add_validation_rule(
            'adaptation',
            self._validate_adaptation
        )

    async def _validate_pattern_detection(self,
                                        current: Dict,
                                        next_state: Dict) -> bool:
        """Validate pattern detection state transitions"""
        # Ensure pattern confidence is valid
        if not 0 <= next_state.get('confidence', 0) <= 1:
            return False

        # Validate pattern metadata
        metadata = next_state.get('metadata', {})
        if not all(isinstance(v, (int, float, str, bool))
                  for v in metadata.values()):
            return False

        return True

    async def _validate_adaptation(self,
                                 current: Dict,
                                 next_state: Dict) -> bool:
        """Validate adaptation state transitions"""
        # Ensure adaptation target exists
        if 'target' not in next_state:
            return False

        # Validate rollback plan
        if 'rollback_plan' not in next_state:
            return False

        # Check adaptation dependencies
        deps = next_state.get('dependencies', [])
        if not all(isinstance(d, str) for d in deps):
            return False

        return True

    async def process_event_stream(self, stream: AsyncIterator[SystemEvent]):
        """Process stream of system events"""
        async for event in stream:
            try:
                # Run all relevant detectors concurrently
                detection_tasks = [
                    detector.analyze(event)
                    for detector in self.detectors.values()
                    if detector.can_handle(event.type)
                ]

                results = await asyncio.gather(*detection_tasks)

                # Correlate patterns across subsystems
                correlated = await self._correlate_patterns(results)

                if correlated.significance > 0.9:
                    # Update state with new pattern
                    await self.state_manager.update_state(
                        'pattern_detection',
                        {
                            'pattern': correlated.to_dict(),
                            'confidence': correlated.confidence,
                            'timestamp': datetime.now(timezone.utc)
                        }
                    )

                    # Store pattern with full context
                    await self.pattern_store.store(
                        pattern=correlated,
                        context=await self._capture_full_context(),
                        metadata={
                            'confidence': correlated.confidence,
                            'impact_score': correlated.impact_score,
                            'subsystems': correlated.affected_subsystems
                        }
                    )

                    # Trigger system adaptation if pattern is strong
                    if correlated.requires_adaptation:
                        await self._adapt_system(correlated)

                except Exception as e:
                logging.error(f"Error processing event: {e}")
                    continue

    async def _adapt_system(self, pattern: Pattern):
        """Adapt system based on detected pattern"""
        # Capture pre-adaptation state
        pre_state = await self._capture_system_state()

        try:
            # Generate adaptation plan
            adaptations = pattern.generate_adaptations()

            # Order adaptations by dependencies
            ordered = self._order_adaptations(adaptations)

            # Apply adaptations in order
            for adaptation in ordered:
                # Update adaptation state
                await self.state_manager.update_state(
                    'adaptation',
                    {
                        'target': adaptation.target,
                        'changes': adaptation.changes,
                        'rollback_plan': adaptation.rollback_plan,
                        'dependencies': adaptation.dependencies,
                        'timestamp': datetime.now(timezone.utc)
                    }
                )

                # Apply adaptation
                await self.system.adapt_component(
                    component=adaptation.target,
                    changes=adaptation.changes,
                    rollback_plan=adaptation.rollback_plan
                )

            # Verify adaptation success
            post_state = await self._capture_system_state()
            if not self._verify_adaptation(pre_state, post_state, pattern):
                # Rollback if verification fails
                await self._rollback_adaptations(ordered)
                raise RuntimeError("Adaptation verification failed")

            # Record successful adaptation
            await self.pattern_store.record_adaptation(
                pattern=pattern,
                pre_state=pre_state,
                post_state=post_state,
                adaptations=ordered
            )

        except Exception as e:
            logging.error(f"Adaptation failed: {e}")
            # Ensure rollback on any error
            await self._rollback_adaptations(ordered)
            raise

    def _order_adaptations(self,
                          adaptations: List[Adaptation]) -> List[Adaptation]:
        """Order adaptations based on dependencies"""
        ordered = []
        remaining = set(range(len(adaptations)))

        while remaining:
            # Find adaptation with satisfied dependencies
            for i in remaining:
                adaptation = adaptations[i]
                if all(dep in {a.target for a in ordered}
                      for dep in adaptation.dependencies):
                    ordered.append(adaptation)
                    remaining.remove(i)
                    break
            else:
                raise RuntimeError("Circular adaptation dependencies")

        return ordered

    async def _rollback_adaptations(self, adaptations: List[Adaptation]):
        """Rollback adaptations in reverse order"""
        for adaptation in reversed(adaptations):
            try:
                await self.system.rollback_adaptation(
                    component=adaptation.target,
                    rollback_plan=adaptation.rollback_plan
                )
                    except Exception as e:
                logging.error(f"Rollback failed for {adaptation.target}: {e}")

    def _verify_adaptation(self,
                          pre_state: Dict,
                          post_state: Dict,
                          pattern: Pattern) -> bool:
        """Verify adaptation success"""
        # Check system stability
        if not self._is_system_stable(post_state):
            return False

        # Verify pattern-specific expectations
        for validation in pattern.validation_rules:
            if not validation(pre_state, post_state):
                return False

        return True

    async def _capture_full_context(self) -> Dict:
        """Capture complete system context"""
        return {
            'system_state': await self._capture_system_state(),
            'ide_state': {
                name: await bridge.capture_state()
                for name, bridge in self.detectors['ide'].bridges.items()
            },
            'shell_state': await self.session_manager.capture_state(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    async def _correlate_patterns(self,
                                detector_results: List[Pattern]) -> Pattern:
        """Correlate patterns across detectors"""
        # Group patterns by timestamp proximity
        grouped = defaultdict(list)
        for pattern in detector_results:
            key = pattern.timestamp.replace(microsecond=0)
            grouped[key].append(pattern)

        # Find correlations
        correlations = []
        for timestamp, patterns in grouped.items():
            if len(patterns) > 1:
                correlation = self._calculate_correlation(patterns)
                if correlation > 0.7:
                    correlations.append(Pattern(
                        id=f"correlation_{uuid.uuid4()}",
                        type="cross_system_correlation",
                        data={
                            'patterns': [p.data for p in patterns],
                            'correlation_score': correlation,
                            'affected_subsystems': self._get_affected_subsystems(patterns)
                        },
                        significance=correlation,
                        timestamp=timestamp,
                        requires_adaptation=any(p.requires_adaptation for p in patterns)
                    ))

        # Return strongest correlation
        return max(correlations,
                  key=lambda p: p.significance) if correlations else None

    def _calculate_correlation(self, patterns: List[Pattern]) -> float:
        """Calculate correlation strength between patterns"""
        # Implement correlation logic
        return 0.8  # Placeholder

    def _get_affected_subsystems(self, patterns: List[Pattern]) -> Set[str]:
        """Get set of affected subsystems"""
        subsystems = set()
        for pattern in patterns:
            if pattern.type.startswith('shell_'):
                subsystems.add('shell')
            elif pattern.type.startswith('ide_'):
                subsystems.add('ide')
            elif pattern.type.startswith('llm_'):
                subsystems.add('llm')
        return subsystems

    def _is_system_stable(self, state: Dict) -> bool:
        """Check if system is in a stable state"""
        # Implement stability checks
        return True  # Placeholder

@dataclass
class Interaction:
    """Real-world interaction with context"""
    id: str
    type: str
    source: str
    prompt: str
    history: List[Dict]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict = field(default_factory=dict)
    was_successful: bool = True

@dataclass
class Response:
    """Response from LLM with metadata"""
    content: str
    source: str
    duration: float
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

class LLMEndpoint:
    """Real LLM endpoint with specialization"""

    def __init__(self, address: str, specialties: List[str]):
        self.address = address
        self.specialties = set(specialties)
        self.performance = defaultdict(list)
        self._session = None
        self._lock = asyncio.Lock()

    async def process(self,
                     prompt: str,
                     context: Context,
                     history: List[Dict]) -> Response:
        """Process request with context"""
        start_time = datetime.now()
        try:
            # Ensure session exists
            if not self._session:
                self._session = aiohttp.ClientSession()

            # Send request with context
            async with self._lock:
                response = await self._session.post(
                    f"http://{self.address}/v1/completions",
                    json={
                        'prompt': prompt,
                        'context': context.to_dict(),
                        'history': history,
                        'specialties': list(self.specialties)
                    }
                )

                if response.status != 200:
                    raise RuntimeError(f"Request failed: {response.status}")

                result = await response.json()

            duration = (datetime.now() - start_time).total_seconds()

            # Record performance
            self.performance[context.type].append({
                'duration': duration,
                'success': True,
                'timestamp': start_time
            })

            return Response(
                content=result['content'],
                source=self.address,
                duration=duration,
                metadata=result.get('metadata', {})
            )

            except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()

            # Record failure
            self.performance[context.type].append({
                'duration': duration,
                'success': False,
                'error': str(e),
                'timestamp': start_time
            })

            return Response(
                content="",
                source=self.address,
                duration=duration,
                error=str(e)
            )

    def get_performance(self, interaction_type: str) -> Dict:
        """Get performance metrics for interaction type"""
        recent = self.performance[interaction_type][-100:]
        if not recent:
            return {
                'success_rate': 1.0,
                'avg_duration': 0.0,
                'error_rate': 0.0
            }

        successes = sum(1 for p in recent if p['success'])
        total_time = sum(p['duration'] for p in recent)

        return {
            'success_rate': successes / len(recent),
            'avg_duration': total_time / len(recent),
            'error_rate': (len(recent) - successes) / len(recent)
        }

class ShellEnhancer:
    """Practical shell environment enhancement"""

    def __init__(self, features_dir: str, history_file: str):
        self.features_dir = Path(features_dir).expanduser()
        self.history_file = Path(history_file).expanduser()
        self.features = {}
        self._setup_features()

    def _setup_features(self):
        """Load shell enhancement features"""
        self.features_dir.mkdir(parents=True, exist_ok=True)

        # Load all feature modules
        for feature_file in self.features_dir.glob('*.py'):
            try:
                # Import feature module
                spec = importlib.util.spec_from_file_location(
                    feature_file.stem,
                    feature_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Register feature
                if hasattr(module, 'setup_feature'):
                    self.features[feature_file.stem] = module.setup_feature()

            except Exception as e:
                logging.error(f"Failed to load feature {feature_file}: {e}")

    async def get_context(self) -> Dict:
        """Get current shell context"""
        # Get command history
        history = await self._get_recent_history()

        # Get active features
        active_features = {
            name: feature.get_state()
            for name, feature in self.features.items()
            if feature.is_active()
        }

        return {
            'history': history,
            'features': active_features,
            'cwd': os.getcwd(),
            'env': dict(os.environ)
        }

    async def _get_recent_history(self, limit: int = 100) -> List[Dict]:
        """Get recent command history"""
        async with aiosqlite.connect(self.history_file) as db:
            cursor = await db.execute("""
                SELECT command, timestamp, exit_code
                FROM history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            rows = await cursor.fetchall()
            return [
                {
                    'command': row[0],
                    'timestamp': datetime.fromisoformat(row[1]),
                    'exit_code': row[2]
                }
                for row in rows
            ]

class SystemCore:
    """Core system with practical tools and real interaction handling"""

    def __init__(self):
        # Real tools, no quantum nonsense
        self.llm_network = {
            'ollama': LLMEndpoint('localhost:11434', specialties=['code', 'refactor']),
            'lmstudio': LLMEndpoint('localhost:1234', specialties=['arch', 'plan']),
            'tgpt': LLMEndpoint('localhost:4891', specialties=['shell', 'docs'])
        }

        # IDE bridges that actually work
        self.ide_bridges = {
            'cursor': IDEBridge(port=9123),
            'warp': IDEBridge(port=9124),
            'windsurf': IDEBridge(port=9125)
        }

        # Practical shell enhancement
        self.shell = ShellEnhancer(
            features_dir='~/.config/shell/features',
            history_file='~/.shell_history.db'
        )

        # Pattern tracking that matters
        self.pattern_engine = PatternEngine(
            storage=SQLiteStorage('patterns.db'),
            min_occurrences=3,
            confidence_threshold=0.85
        )

    async def process_interaction(self, interaction: Interaction):
        """Process real-world interaction"""
        # Extract real context
        context = await self._gather_context(interaction)

        # Route to best LLM
        llm = await self._select_llm(context)

        # Get meaningful response
        response = await llm.process(
            prompt=interaction.prompt,
            context=context,
            history=interaction.history[-5:]  # Recent relevant history only
        )

        # Learn from interaction
        await self._learn_from_interaction(
            context=context,
            response=response,
            success=interaction.was_successful
        )

        return response

    async def _gather_context(self, interaction: Interaction) -> Context:
        """Gather real-world context"""
        # Get IDE state if relevant
        ide_state = await self.ide_bridges[interaction.source].get_state() if interaction.source in self.ide_bridges else None

        # Get shell context if needed
        shell_context = await self.shell.get_context() if interaction.type == 'shell' else None

        # Get relevant patterns
        patterns = await self.pattern_engine.get_relevant_patterns(
            interaction_type=interaction.type,
            window=timedelta(minutes=30)
        )

        return Context(
            ide_state=ide_state,
            shell_context=shell_context,
            patterns=patterns,
            timestamp=datetime.now(timezone.utc)
        )

    async def _select_llm(self, context: Context) -> LLMEndpoint:
        """Select best LLM for context"""
        scores = {}
        for name, llm in self.llm_network.items():
            # Calculate base score from performance
            perf = llm.get_performance(context.type)
            base_score = (
                perf['success_rate'] * 0.4 +
                (1 - perf['error_rate']) * 0.3 +
                (1 / (1 + perf['avg_duration'])) * 0.3
            )

            # Adjust for specialties
            specialty_score = self._calculate_specialty_match(
                llm.specialties,
                context
            )

            scores[name] = base_score * 0.7 + specialty_score * 0.3

        # Return LLM with highest score
        best_llm = max(scores.items(), key=lambda x: x[1])[0]
        return self.llm_network[best_llm]

    def _calculate_specialty_match(self,
                                 specialties: Set[str],
                                 context: Context) -> float:
        """Calculate how well specialties match context"""
        if not specialties:
            return 0.0

        matches = 0
        if context.ide_state and any(s in {'code', 'refactor'} for s in specialties):
            matches += 1
        if context.shell_context and 'shell' in specialties:
            matches += 1

        return matches / len(specialties)

    async def _learn_from_interaction(self,
                                    context: Context,
                                    response: Response,
                                    success: bool):
        """Learn from real interaction"""
        if success:
            # Record successful pattern
            await self.pattern_engine.record_success(
                context=context,
                response=response
            )

            # Adapt routing if needed
            await self._adapt_routing(context, response)

        else:
            # Learn from failure
            await self.pattern_engine.record_failure(
                context=context,
                response=response,
                error=response.error
            )

    async def _adapt_routing(self, context: Context, response: Response):
        """Adapt routing based on successful interaction"""
        # Update LLM specialization scores
        llm = self.llm_network[response.source]
        specialties = self._identify_used_specialties(context, response)

        for specialty in specialties:
            if specialty in llm.specialties:
                # Reinforce successful specialty use
                current_score = llm.get_performance(context.type)['success_rate']
                new_score = current_score * 0.9 + 0.1  # Gradual improvement

                await self.pattern_engine.record_specialty_effectiveness(
                    llm=response.source,
                    specialty=specialty,
                    score=new_score
                )

    def _identify_used_specialties(self,
                                 context: Context,
                                 response: Response) -> Set[str]:
        """Identify which specialties were actually used"""
        specialties = set()

        # Check for code-related specialties
        if context.ide_state and 'code' in response.content.lower():
            specialties.add('code')

        # Check for shell specialties
        if context.shell_context and 'command' in response.content.lower():
            specialties.add('shell')

        return specialties

@dataclass
class CommandChain:
    """Represents a chain of shell commands"""
    text: str
    commands: List[str]
    is_chain: bool = True
    failed: bool = False
    error: Optional[str] = None

@dataclass
class CodeSuggestion:
    """Code improvement suggestion"""
    content: str
    explanation: str
    confidence: float
    line_number: Optional[int] = None
    is_safe: bool = True

@dataclass
class Error:
    """System error with context"""
    message: str
    traceback: str
    context: Dict
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class Solution:
    """Error solution with safety check"""
    fix: str
    explanation: str
    confidence: float
    is_safe: bool
    requires_review: bool = False

class OllamaEngine:
    """Local Ollama LLM engine"""

    def __init__(self, models: Dict[str, str]):
        self.models = models
        self.sessions = {}
        self._lock = asyncio.Lock()

    async def analyze_code_realtime(self,
                                  code: str,
                                  cursor_position: int,
                                  language: str) -> List[CodeSuggestion]:
        """Analyze code in real-time"""
        model = 'codellama'  # Best for code

        async with self._get_session(model) as session:
            response = await session.post('/api/analyze', json={
                'code': code,
                'cursor': cursor_position,
                'language': language
            })

                        if response.status != 200:
                return []

            suggestions = []
            for item in await response.json():
                suggestions.append(CodeSuggestion(
                    content=item['suggestion'],
                    explanation=item['reason'],
                    confidence=item['confidence'],
                    line_number=item.get('line'),
                    is_safe=item.get('safe', True)
                ))

            return suggestions

    async def generate_docs(self,
                          code: str,
                          style: str = 'google') -> str:
        """Generate code documentation"""
        model = 'mistral'  # Best for technical writing

        async with self._get_session(model) as session:
            response = await session.post('/api/docs', json={
                'code': code,
                'style': style
            })

            if response.status != 200:
                return ""

            result = await response.json()
            return result['documentation']

    async def fix_command(self,
                         command: str,
                         error: str) -> str:
        """Fix failed shell command"""
        model = 'llama2'  # Good for general tasks

        async with self._get_session(model) as session:
            response = await session.post('/api/fix', json={
                'command': command,
                'error': error
            })

            if response.status != 200:
                return command

            result = await response.json()
            return result['fixed_command']

    async def solve_error(self,
                         error: Error,
                         context: Dict) -> Solution:
        """Generate error solution"""
        model = 'codellama'  # Best for code issues

        async with self._get_session(model) as session:
            response = await session.post('/api/solve', json={
                'error': error.message,
                'traceback': error.traceback,
                'context': context
            })

            if response.status != 200:
                return Solution(
                    fix="",
                    explanation="Failed to generate solution",
                    confidence=0.0,
                    is_safe=False,
                    requires_review=True
                            )

                        result = await response.json()
            return Solution(
                fix=result['solution'],
                explanation=result['explanation'],
                confidence=result['confidence'],
                is_safe=result['safe'],
                requires_review=not result['safe']
            )

    @asynccontextmanager
    async def _get_session(self, model: str):
        """Get or create model session"""
        if model not in self.sessions:
            async with self._lock:
                if model not in self.sessions:
                    self.sessions[model] = aiohttp.ClientSession(
                        base_url='http://localhost:11434'
                    )

        try:
            yield self.sessions[model]
        except Exception as e:
            logging.error(f"Ollama session error: {e}")
            # Cleanup session on error
            if model in self.sessions:
                await self.sessions[model].close()
                del self.sessions[model]
            raise

class LMStudioEngine:
    """Local LM Studio engine"""

    def __init__(self, models: Dict[str, str]):
        self.models = models
        self.client = None
        self._lock = asyncio.Lock()

    async def analyze_code(self,
                          code: str,
                          context: Dict) -> Dict:
        """Deep code analysis"""
        model = 'wizardcoder'  # Best for code review

        async with self._get_client() as client:
            response = await client.post(
                '/api/analyze',
                json={
                    'code': code,
                    'context': context,
                    'model': model
                }
            )

            if response.status != 200:
                return {}

            return await response.json()

    async def plan_architecture(self,
                              requirements: str,
                              constraints: Dict) -> Dict:
        """Generate architecture plan"""
        model = 'deepseek'  # Best for architecture

        async with self._get_client() as client:
            response = await client.post(
                '/api/plan',
                json={
                    'requirements': requirements,
                    'constraints': constraints,
                    'model': model
                }
            )

            if response.status != 200:
                return {}

            return await response.json()

    @asynccontextmanager
    async def _get_client(self):
        """Get or create API client"""
        if not self.client:
            async with self._lock:
                if not self.client:
                    self.client = aiohttp.ClientSession(
                        base_url='http://localhost:1234'
                    )

        try:
            yield self.client
        except Exception as e:
            logging.error(f"LM Studio client error: {e}")
            if self.client:
                await self.client.close()
                self.client = None
            raise

class AugmentedDev:
    """Development environment augmentation"""

    def __init__(self):
        # Real IDE bridges
        self.ides = {
            'cursor': CursorBridge(port=9123),
            'warp': WarpBridge(port=9124),
            'windsurf': WarpBridge(port=9125)
        }

        # Local LLMs for different strengths
        self.llms = {
            'ollama': OllamaEngine(
                models={
                    'codellama': 'code generation/completion',
                    'mistral': 'technical writing/docs',
                    'llama2': 'general assistance'
                }
            ),
            'lmstudio': LMStudioEngine(
                models={
                    'wizardcoder': 'code analysis/review',
                    'deepseek': 'architecture/planning'
                }
            )
        }

        # Zellij for persistent terminal state
        self.zellij = ZellijManager(
            layout='dev.kdl',
            panes={
                'main': 'primary terminal',
                'repl': 'python/node REPL',
                'logs': 'system logs',
                'ai': 'AI interaction'
            }
        )

        # Error handling
        self.error_store = SQLiteStorage('errors.db')

    async def augment_workflow(self, context: Context):
        """Augment development workflow in real-time"""
        # Real-time code understanding
        if context.in_ide:
            current_file = await self.ides[context.ide].get_current_file()

            # Proactive suggestions based on what you're typing
            if current_file.is_code:
                suggestions = await self.llms['ollama'].analyze_code_realtime(
                    code=current_file.content,
                    cursor_position=current_file.cursor,
                    language=current_file.language
                )

                if suggestions.has_improvements:
                    await self.ides[context.ide].show_suggestions(suggestions)

            # Auto-generate docs while you code
            elif current_file.needs_documentation:
                docs = await self.llms['ollama'].generate_docs(
                    code=current_file.content,
                    style='google'  # or whatever your team uses
                )

                await self.ides[context.ide].insert_docs(docs)

        # Terminal augmentation
        elif context.in_terminal:
            command = context.current_command

            # Command chain optimization
            if command.is_chain:
                optimized = await self.optimize_command_chain(command)
                await self.zellij.suggest_optimization(optimized)

            # Auto-fix failed commands
            elif command.failed:
                fix = await self.llms['ollama'].fix_command(
                    command=command.text,
                    error=command.error
                )
                await self.zellij.suggest_fix(fix)

    async def optimize_command_chain(self, chain: CommandChain):
        """Optimize shell command chains"""
        # Analyze command chain
        analysis = await self.llms['ollama'].analyze_commands(chain)

        if analysis.can_parallelize:
            return ParallelizedChain(
                commands=chain.commands,
                dependencies=analysis.dependencies
            )

        elif analysis.has_better_tool:
            return ToolSuggestion(
                current=chain.text,
                suggestion=analysis.better_tool,
                reason=analysis.explanation
            )

        elif analysis.can_simplify:
            return SimplifiedChain(
                original=chain.text,
                simplified=analysis.simplified,
                alias_suggestion=analysis.generate_alias()
            )

    async def handle_error(self, error: Error):
        """Handle system errors intelligently"""
        # Get error context
        context = await self._gather_error_context(error)

        # Find similar errors in history
        similar = await self.find_similar_errors(error)

        if similar:
            # Use historical solutions
            solution = await self.apply_historical_fix(error, similar)
        else:
            # Generate new solution
            solution = await self.llms['ollama'].solve_error(
                error=error,
                context=context
            )

        # Apply fix if safe
        if solution.is_safe:
            await self.apply_fix(solution)
        else:
            await self.suggest_fix(solution)

    async def find_similar_errors(self, error: Error) -> List[Dict]:
        """Find similar historical errors"""
        return await self.error_store.find_similar({
            'message': error.message,
            'context': error.context
        })

    async def apply_historical_fix(self,
                                 error: Error,
                                 similar: List[Dict]) -> Solution:
        """Apply fix from similar historical error"""
        # Get most successful fix
        best_fix = max(similar,
                      key=lambda x: x['success_rate'])

        return Solution(
            fix=best_fix['solution'],
            explanation=best_fix['explanation'],
            confidence=best_fix['success_rate'],
            is_safe=best_fix['is_safe']
        )

    async def apply_fix(self, solution: Solution):
        """Apply error fix"""
        if solution.requires_review:
            await self.suggest_fix(solution)
            return

        try:
            if solution.is_safe:
                # Apply fix automatically
                await self._apply_solution(solution)

                # Record successful fix
                await self.error_store.record_success(solution)

        except Exception as e:
            logging.error(f"Failed to apply fix: {e}")
            await self.error_store.record_failure(solution)

    async def suggest_fix(self, solution: Solution):
        """Suggest fix to user"""
        await self.zellij.show_suggestion({
            'title': 'Error Fix Suggestion',
            'solution': solution.fix,
            'explanation': solution.explanation,
            'confidence': solution.confidence
        })

@dataclass
class CodeAnalysis:
    """Code analysis result with confidence"""
    suggestions: List[Dict]
    examples: List[Dict]
    confidence: float
    requires_action: bool = False

@dataclass
class ProjectContext:
    """Project-wide context and patterns"""
    patterns: List[Dict]
    recent_files: List[str]
    active_features: List[str]
    metadata: Dict = field(default_factory=dict)

class CodeAnalyzer:
    """Real-time code analysis engine"""

    def __init__(self, models: Dict[str, Dict]):
        self.models = models
        self._session = None
        self._cache = LRUCache(maxsize=1000)

    async def suggest_implementation(self,
                                  intent: Dict,
                                  similar_code: List[Dict],
                                  project_patterns: List[Dict]) -> CodeAnalysis:
        """Generate implementation suggestions"""
        model = self.models.get('codellama:13b')
        if not model:
            return CodeAnalysis([], [], 0.0)

        cache_key = f"impl_{hash(str(intent))}"
        if cached := self._cache.get(cache_key):
            return cached

        try:
            if not self._session:
                self._session = aiohttp.ClientSession()

            # Analyze intent and context
            analysis = await self._analyze_implementation_context(
                intent=intent,
                similar_code=similar_code,
                patterns=project_patterns
            )

            # Generate suggestions
            suggestions = []
            examples = []
            confidence = 0.0

            if analysis['matches_patterns']:
                # Use project patterns for consistent implementation
                suggestions.extend(
                    self._generate_pattern_based_suggestions(
                        analysis['relevant_patterns']
                    )
                )
                confidence = max(confidence, 0.9)

            if analysis['has_similar_code']:
                # Learn from similar implementations
                examples.extend(analysis['similar_implementations'])
                suggestions.extend(
                    self._generate_similarity_based_suggestions(
                        analysis['similar_implementations']
                    )
                )
                confidence = max(confidence, 0.85)

            result = CodeAnalysis(
                suggestions=suggestions,
                examples=examples,
                confidence=confidence,
                requires_action=confidence > 0.8
            )

            # Cache result
            self._cache.put(cache_key, result)
                        return result

        except Exception as e:
            logging.error(f"Implementation suggestion failed: {e}")
            return CodeAnalysis([], [], 0.0)

    async def preview_refactor(self,
                             target_code: str,
                             impact: Dict) -> CodeAnalysis:
        """Generate refactoring preview"""
        model = self.models.get('deepseek:67b')
        if not model:
            return CodeAnalysis([], [], 0.0)

        try:
            # Analyze refactoring impact
            if impact['high_risk_changes']:
                return CodeAnalysis(
                    suggestions=[{
                        'type': 'warning',
                        'message': 'High risk refactoring detected',
                        'details': impact['risk_details']
                    }],
                    examples=[],
                    confidence=0.9,
                    requires_action=True
                )

            # Generate refactoring suggestions
            suggestions = []
            examples = []

            if impact['pattern_violations']:
                suggestions.extend([
                    {
                        'type': 'pattern_fix',
                        'violation': v,
                        'suggestion': self._generate_pattern_fix(v)
                    }
                    for v in impact['pattern_violations']
                ])

            if impact['similar_refactors']:
                examples.extend(impact['similar_refactors'])
                suggestions.extend([
                    {
                        'type': 'similar_refactor',
                        'example': e,
                        'suggestion': self._adapt_similar_refactor(e, target_code)
                    }
                    for e in impact['similar_refactors']
                ])

            return CodeAnalysis(
                suggestions=suggestions,
                examples=examples,
                confidence=0.85 if suggestions else 0.0,
                requires_action=bool(suggestions)
            )

        except Exception as e:
            logging.error(f"Refactor preview failed: {e}")
            return CodeAnalysis([], [], 0.0)

    async def suggest_fix(self,
                         error: Dict,
                         similar_fixes: List[Dict],
                         project_context: Dict) -> CodeAnalysis:
        """Suggest error fixes"""
        try:
            # Analyze error context
            analysis = await self._analyze_error_context(
                error=error,
                similar_fixes=similar_fixes,
                context=project_context
            )

            suggestions = []
            examples = []
            confidence = 0.0

            if analysis['known_pattern']:
                # Use known fix patterns
                suggestions.append({
                    'type': 'pattern_fix',
                    'pattern': analysis['pattern'],
                    'fix': analysis['pattern_fix']
                })
                confidence = 0.95

            elif analysis['similar_fixes']:
                # Adapt similar fixes
                examples.extend(analysis['similar_fixes'])
                suggestions.extend([
                    {
                        'type': 'similar_fix',
                        'original': fix,
                        'adapted': self._adapt_fix(fix, error)
                    }
                    for fix in analysis['similar_fixes']
                ])
                confidence = 0.85

            else:
                # Generate new fix
                suggested_fix = await self._generate_fix(error, project_context)
                if suggested_fix:
                    suggestions.append({
                        'type': 'generated_fix',
                        'fix': suggested_fix,
                        'explanation': suggested_fix['explanation']
                    })
                    confidence = 0.75

            return CodeAnalysis(
                suggestions=suggestions,
                examples=examples,
                confidence=confidence,
                requires_action=confidence > 0.8
            )

        except Exception as e:
            logging.error(f"Fix suggestion failed: {e}")
            return CodeAnalysis([], [], 0.0)

class IDEAugmenter:
    """Real-time IDE augmentation with intelligent assistance"""

    def __init__(self):
        # Real-time code analysis pipeline
        self.code_analyzer = CodeAnalyzer(
            models={
                'codellama:13b': {
                    'purpose': 'real-time completion',
                    'context_window': 8192
                },
                'deepseek:67b': {
                    'purpose': 'deep code understanding',
                    'context_window': 32768
                }
            }
        )

        # Project-wide understanding
        self.project_context = ProjectContext(
            patterns=[],
            recent_files=[],
            active_features=[]
        )

        # Terminal integration
        self.zellij = ZellijSession(
            layout='dev.kdl',
            panes=['code', 'terminal', 'ai']
        )

        # State management
        self.state_manager = StateManager()
        self._setup_state_validation()

    def _setup_state_validation(self):
        """Setup state validation rules"""
        self.state_manager.add_validation_rule(
            'ide_state',
            self._validate_ide_state
        )
        self.state_manager.add_validation_rule(
            'analysis_state',
            self._validate_analysis_state
        )

    async def _validate_ide_state(self,
                                current: Dict,
                                next_state: Dict) -> bool:
        """Validate IDE state transitions"""
        # Ensure required fields
        required = {'file', 'cursor', 'view', 'mode'}
        if not all(field in next_state for field in required):
            return False

        # Validate cursor position
        if not isinstance(next_state['cursor'], dict) or \
           'line' not in next_state['cursor'] or \
           'column' not in next_state['cursor']:
            return False

        return True

    async def _validate_analysis_state(self,
                                     current: Dict,
                                     next_state: Dict) -> bool:
        """Validate analysis state transitions"""
        # Ensure analysis metadata
        if 'timestamp' not in next_state or \
           'confidence' not in next_state:
            return False

        # Validate confidence
        if not 0 <= next_state['confidence'] <= 1:
            return False

        return True

    async def watch_coding_session(self):
        """Watch coding session for assistance opportunities"""
        while True:
            try:
                # Get real-time IDE state
                ide_state = await self.get_ide_state()

                if ide_state.is_coding:
                    # Update state
                    await self.state_manager.update_state(
                        'ide_state',
                        {
                            'file': ide_state.current_file,
                            'cursor': ide_state.cursor_position,
                            'view': ide_state.view_state,
                            'mode': 'coding',
                            'timestamp': datetime.now(timezone.utc)
                        }
                    )

                    # What are they trying to do?
                    intent = await self.analyze_coding_intent(ide_state)

                    if intent.is_implementing_feature:
                        await self._assist_feature_implementation(intent)
                    elif intent.is_refactoring:
                        await self._assist_refactoring(intent)
                    elif intent.is_debugging:
                        await self._assist_debugging(intent)

                await asyncio.sleep(0.1)  # Rate limit

        except Exception as e:
                logging.error(f"Coding session watch failed: {e}")
                await asyncio.sleep(1.0)  # Longer delay on error

    async def _assist_feature_implementation(self, intent: Dict):
        """Assist with feature implementation"""
        try:
            # Pull relevant code examples from project
            similar_code = await self.project_context.find_similar_code(intent)

            # Generate implementation suggestion
            suggestion = await self.code_analyzer.suggest_implementation(
                intent=intent,
                similar_code=similar_code,
                project_patterns=self.project_context.patterns
            )

            # Update analysis state
            await self.state_manager.update_state(
                'analysis_state',
                {
                    'type': 'implementation',
                    'suggestion': suggestion.to_dict(),
                    'confidence': suggestion.confidence,
                    'timestamp': datetime.now(timezone.utc)
                }
            )

            if suggestion.confidence > 0.8:
                # Show inline suggestion
                await self.show_inline_suggestion(suggestion)

                # Open relevant examples in split view
                if suggestion.has_examples:
                    await self.show_examples(suggestion.examples)

        except Exception as e:
            logging.error(f"Feature implementation assistance failed: {e}")

    async def _assist_refactoring(self, intent: Dict):
        """Assist with code refactoring"""
        try:
            # Analyze impact
            impact = await self.project_context.analyze_refactor_impact(intent)

            if impact.is_safe:
                # Generate refactor preview
                preview = await self.code_analyzer.preview_refactor(
                    target_code=intent.target,
                    impact=impact
                )

                # Update analysis state
                await self.state_manager.update_state(
                    'analysis_state',
                    {
                        'type': 'refactor',
                        'preview': preview.to_dict(),
                        'impact': impact.to_dict(),
                        'confidence': preview.confidence,
                        'timestamp': datetime.now(timezone.utc)
                    }
                )

                # Show split diff view
                await self.show_refactor_preview(preview)

                # Prepare automated tests
                tests = await self.generate_safety_tests(impact)

                await self.show_test_plan(tests)

        except Exception as e:
            logging.error(f"Refactoring assistance failed: {e}")

    async def _assist_debugging(self, intent: Dict):
        """Assist with debugging"""
        try:
            # Get error context
            error = await self.get_error_context(intent)

            # Find similar errors in history
            similar = await self.project_context.find_similar_errors(error)

            if similar:
                # Show how these were fixed before
                await self.show_similar_fixes(similar)

            # Generate fix suggestion
            fix = await self.code_analyzer.suggest_fix(
                error=error,
                similar_fixes=similar,
                project_context=self.project_context
            )

            # Update analysis state
            await self.state_manager.update_state(
                'analysis_state',
                {
                    'type': 'debug',
                    'error': error,
                    'fix': fix.to_dict(),
                    'confidence': fix.confidence,
                    'timestamp': datetime.now(timezone.utc)
                }
            )

            if fix.confidence > 0.9:
                # Show quick-fix option
                await self.show_quick_fix(fix)

                # Explain the fix in the AI pane
                await self.zellij.panes['ai'].explain_fix(fix)

        except Exception as e:
            logging.error(f"Debugging assistance failed: {e}")

    async def show_inline_suggestion(self, suggestion: CodeAnalysis):
        """Show inline code suggestion"""
        try:
            # Show ghost text
            await self.ide.show_ghost_text(
                text=suggestion.code,
                line=suggestion.line,
                confidence=suggestion.confidence
            )

            # Show explanation in hover
            await self.ide.register_hover_handler(
                line=suggestion.line,
                content=suggestion.explanation
            )

        except Exception as e:
            logging.error(f"Failed to show inline suggestion: {e}")

    async def show_examples(self, examples: List[Dict]):
        """Show relevant code examples"""
        try:
            # Open examples in split view
            for example in examples:
                await self.ide.open_file(
                    file=example['file'],
                    line=example['line'],
                    split='right'
                )

        except Exception as e:
            logging.error(f"Failed to show examples: {e}")

    async def show_refactor_preview(self, preview: CodeAnalysis):
        """Show refactoring preview"""
        try:
            # Show diff view
            await self.ide.show_diff(
                original=preview.original,
                modified=preview.modified,
                title="Refactor Preview"
            )

        except Exception as e:
            logging.error(f"Failed to show refactor preview: {e}")

    async def show_test_plan(self, tests: List[Dict]):
        """Show test execution plan"""
        try:
            # Show test plan in AI pane
            await self.zellij.panes['ai'].show_content(
                title="Test Plan",
                content=self._format_test_plan(tests)
            )

        except Exception as e:
            logging.error(f"Failed to show test plan: {e}")

    async def show_similar_fixes(self, fixes: List[Dict]):
        """Show similar error fixes"""
        try:
            # Show fixes in AI pane
            await self.zellij.panes['ai'].show_content(
                title="Similar Fixes",
                content=self._format_similar_fixes(fixes)
            )

        except Exception as e:
            logging.error(f"Failed to show similar fixes: {e}")

    async def show_quick_fix(self, fix: CodeAnalysis):
        """Show quick fix option"""
        try:
            # Show quick fix lightbulb
            await self.ide.show_quick_fix(
                line=fix.line,
                fix=fix.suggestion,
                explanation=fix.explanation
            )

        except Exception as e:
            logging.error(f"Failed to show quick fix: {e}")

    def _format_test_plan(self, tests: List[Dict]) -> str:
        """Format test plan for display"""
        sections = []
        for test in tests:
            sections.append(f"## {test['name']}\n")
            sections.append(f"Purpose: {test['purpose']}\n")
            sections.append("```python\n{test['code']}\n```\n")
        return "\n".join(sections)

    def _format_similar_fixes(self, fixes: List[Dict]) -> str:
        """Format similar fixes for display"""
        sections = []
        for fix in fixes:
            sections.append(f"## Similar Error\n")
            sections.append(f"Error: {fix['error']}\n")
            sections.append(f"Fix: {fix['solution']}\n")
            sections.append(f"Explanation: {fix['explanation']}\n")
        return "\n".join(sections)
