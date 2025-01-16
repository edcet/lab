"""NFX Quantum AI Gateway Module

Production-ready implementation with load balancing, circuit breaking,
and advanced routing strategies with pattern-based intelligence, bulletproof state management,
and evolutionary agent network.
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional, Set, AsyncIterator, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager, AsyncExitStack
import statistics
import aiohttp
import uuid
import json

from nfx.core.compute.engine import ComputeEngine
from nfx.core.memory.manager import MemoryManager
from nfx.core.neural.memory import NeuralMemoryCore
from nfx.core.neural.reality import RealityManipulator
from nfx.core.neural.fabric import NeuralFabric

# Exception classes
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
    """Analyzes routing behavior patterns"""

    def __init__(self, min_sequence_length: int, max_gap: timedelta):
        self.min_sequence_length = min_sequence_length
        self.max_gap = max_gap
        self.sequence_buffer = []

    async def analyze(self, data: Dict) -> List[Pattern]:
        """Analyze routing behavior"""
        self.sequence_buffer.append(data)
        self._prune_old_sequences()
        return await self._find_patterns()

    def _prune_old_sequences(self):
        """Remove old sequences"""
        now = datetime.now(timezone.utc)
        self.sequence_buffer = [
            seq for seq in self.sequence_buffer
            if now - seq['timestamp'] <= self.max_gap
        ]

    async def _find_patterns(self) -> List[Pattern]:
        """Find patterns in sequence buffer"""
        patterns = []
        if len(self.sequence_buffer) < self.min_sequence_length:
            return patterns

        # Analyze sequences
        for i in range(len(self.sequence_buffer) - self.min_sequence_length + 1):
            sequence = self.sequence_buffer[i:i + self.min_sequence_length]
            pattern = self._analyze_sequence(sequence)
            if pattern:
                patterns.append(pattern)

        return patterns

    def _analyze_sequence(self, sequence: List[Dict]) -> Optional[Pattern]:
        """Analyze a sequence for patterns"""
        # Calculate sequence characteristics
        durations = []
        models = []
        errors = []

        for item in sequence:
            durations.append(item['duration'])
            models.append(item['model'])
            errors.append(item.get('error', False))

        # Check for patterns
        if self._is_consistent_timing(durations):
            return Pattern(
                id=str(uuid.uuid4()),
                type='timing',
                data={
                    'avg_duration': statistics.mean(durations),
                    'std_dev': statistics.stdev(durations),
                    'sequence': sequence
                },
                significance=0.8,
                timestamp=datetime.now(timezone.utc)
            )

        if self._is_model_pattern(models):
            return Pattern(
                id=str(uuid.uuid4()),
                type='model_usage',
                data={
                    'models': models,
                    'sequence': sequence
                },
                significance=0.9,
                timestamp=datetime.now(timezone.utc)
            )

        if self._is_error_pattern(errors):
            return Pattern(
                id=str(uuid.uuid4()),
                type='error',
                data={
                    'errors': errors,
                    'sequence': sequence
                },
                significance=0.95,
                timestamp=datetime.now(timezone.utc),
                requires_action=True
            )

        return None

    def _is_consistent_timing(self, durations: List[float]) -> bool:
        """Check for consistent timing patterns"""
        if not durations:
            return False

        mean = statistics.mean(durations)
        std_dev = statistics.stdev(durations)
        cv = std_dev / mean  # Coefficient of variation

        return cv < 0.2  # Less than 20% variation

    def _is_model_pattern(self, models: List[str]) -> bool:
        """Check for model usage patterns"""
        if not models:
            return False

        # Check for repeating sequences
        for length in range(1, len(models) // 2 + 1):
            pattern = models[:length]
            if self._is_repeating(models, pattern):
                return True

        return False

    def _is_error_pattern(self, errors: List[bool]) -> bool:
        """Check for error patterns"""
        if not errors:
            return False

        error_rate = sum(1 for e in errors if e) / len(errors)
        return error_rate > 0.3  # More than 30% errors

    def _is_repeating(self, sequence: List[str], pattern: List[str]) -> bool:
        """Check if pattern repeats in sequence"""
        if not pattern:
            return False

        pattern_len = len(pattern)
        if pattern_len == 0:
            return False

        for i in range(0, len(sequence) - pattern_len + 1, pattern_len):
            if sequence[i:i + pattern_len] != pattern:
                return False

        return True

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
    """Advanced task router with pattern-based intelligence"""

    def __init__(self):
        self.metrics = RouterMetrics()
        self.state_manager = StateManager()
        self.behavior_analyzer = BehaviorAnalyzer(
            min_sequence_length=5,
            max_gap=timedelta(minutes=5)
        )
        self._logger = logging.getLogger('task_router')

        # Set up state validation
        self._setup_state_validation()

    def _setup_state_validation(self):
        """Set up state validation rules"""
        self.state_manager.add_validation_rule(
            'router',
            self._validate_router_state
        )
        self.state_manager.add_validation_rule(
            'metrics',
            self._validate_metrics_state
        )

    async def _validate_router_state(self, current: Dict, next_state: Dict) -> bool:
        """Validate router state transition"""
        try:
            # Validate model states
            for model in next_state.get('models', {}):
                if model not in current.get('models', {}):
                    if not self._validate_model_state(model, next_state['models'][model]):
                        return False

            # Validate routing strategy
            if 'strategy' in next_state:
                if next_state['strategy'] not in {'adaptive', 'round_robin', 'least_loaded'}:
                    return False

            return True

        except Exception as e:
            self._logger.error(f"Router state validation failed: {e}")
            return False

    async def _validate_metrics_state(self, current: Dict, next_state: Dict) -> bool:
        """Validate metrics state transition"""
        try:
            # Validate request counts
            for model, count in next_state.get('request_counts', {}).items():
                if count < current.get('request_counts', {}).get(model, 0):
                    return False

            # Validate error counts
            for model, count in next_state.get('error_counts', {}).items():
                if count < current.get('error_counts', {}).get(model, 0):
                    return False

            # Validate load metrics
            for model, load in next_state.get('load_metrics', {}).items():
                if not 0 <= load <= 1:
                    return False

            return True

        except Exception as e:
            self._logger.error(f"Metrics state validation failed: {e}")
            return False

    async def _process_patterns(self, model: str, duration: float, error: bool):
        """Process routing patterns"""
        try:
            # Create pattern data
            pattern_data = {
                'model': model,
                'duration': duration,
                'error': error,
                'timestamp': datetime.now(timezone.utc)
            }

            # Analyze patterns
            patterns = await self.behavior_analyzer.analyze(pattern_data)

            # Store significant patterns
            for pattern in patterns:
                if pattern.significance > 0.8:
                    self.metrics.patterns[pattern.id] = pattern
                    if pattern.requires_action:
                        await self._handle_pattern(pattern)

        except Exception as e:
            self._logger.error(f"Pattern processing failed: {e}")

    async def _handle_pattern(self, pattern: Pattern):
        """Handle actionable patterns"""
        try:
            if pattern.type == 'error':
                # Circuit breaking
                if pattern.data['error_rate'] > 0.5:
                    self._open_circuit(pattern.data['model'])

            elif pattern.type == 'timing':
                # Adjust timeouts
                if pattern.data['avg_duration'] > 5.0:
                    await self._adjust_timeouts(pattern.data['model'])

        except Exception as e:
            self._logger.error(f"Pattern handling failed: {e}")

    async def route_task(self,
                        available_models: Set[str],
                        model_health: Dict[str, bool],
                        model_load: Dict[str, float],
                        required_capabilities: Optional[List[str]] = None,
                        strategy: str = "adaptive") -> Optional[str]:
        """Route task to appropriate model"""
        try:
            # Filter unhealthy and circuit-broken models
            available_models = {
                model for model in available_models
                if model_health.get(model, False)
            }
            available_models = self._filter_circuit_broken(available_models)

            if not available_models:
                self._logger.warning("No available models")
                return None

            # Check load shedding
            if self._should_shed_load(model_load):
                self._logger.warning("Load shedding activated")
                return None

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
            else:
                self._logger.error(f"Unknown routing strategy: {strategy}")
                return None

        except Exception as e:
            self._logger.error(f"Task routing failed: {e}")
            return None

    def _should_shed_load(self, model_load: Dict[str, float]) -> bool:
        """Check if load shedding is needed"""
        if not model_load:
            return False
        return statistics.mean(model_load.values()) > 0.9

    def _filter_circuit_broken(self, models: Set[str]) -> Set[str]:
        """Filter out circuit-broken models"""
        return {
            model for model in models
            if self.metrics.circuit_states.get(model) != "OPEN"
        }

    async def route_adaptive(self,
                           available_models: Set[str],
                           model_health: Dict[str, bool],
                           model_load: Dict[str, float],
                           required_capabilities: Optional[List[str]] = None) -> str:
        """Adaptive routing based on multiple factors"""
        try:
            if not available_models:
                return None

            # Calculate weights
            weights = self._calculate_weights(available_models, model_load)

            # Filter by capabilities
            if required_capabilities:
                available_models = {
                    model for model in available_models
                    if self._has_capabilities(model, required_capabilities)
                }

            # Apply error penalty
            for model in available_models:
                error_score = self._calculate_error_score(model)
                weights[model] *= (1 - error_score)

            # Apply response time bonus
            for model in available_models:
                response_score = self._calculate_response_score(model)
                weights[model] *= (1 + response_score)

            # Route using weighted random selection
            return self.route_weighted_random(available_models, weights)

        except Exception as e:
            self._logger.error(f"Adaptive routing failed: {e}")
            return None

    def route_round_robin(self, available_models: Set[str]) -> str:
        """Simple round-robin routing"""
        try:
            if not available_models:
                return None

            # Get last used timestamps
            timestamps = {
                model: self.metrics.last_used.get(model, datetime.min)
                for model in available_models
            }

            # Select least recently used
            selected = min(timestamps.items(), key=lambda x: x[1])[0]
            self.metrics.last_used[selected] = datetime.now(timezone.utc)

            return selected

        except Exception as e:
            self._logger.error(f"Round-robin routing failed: {e}")
            return None

    def route_least_loaded(self,
                          available_models: Set[str],
                          model_load: Dict[str, float]) -> str:
        """Route to least loaded model"""
        try:
            if not available_models:
                return None

            # Filter models with load info
            models_with_load = {
                model: load
                for model, load in model_load.items()
                if model in available_models
            }

            if not models_with_load:
                return None

            # Select model with minimum load
            return min(models_with_load.items(), key=lambda x: x[1])[0]

        except Exception as e:
            self._logger.error(f"Least-loaded routing failed: {e}")
            return None

    def route_weighted_random(self,
                            available_models: Set[str],
                            weights: Dict[str, float]) -> str:
        """Route using weighted random selection"""
        try:
            if not available_models:
                return None

            # Filter weights for available models
            model_weights = {
                model: weights.get(model, 0)
                for model in available_models
            }

            if not model_weights:
                return None

            # Normalize weights
            total_weight = sum(model_weights.values())
            if total_weight == 0:
                return random.choice(list(available_models))

            normalized_weights = {
                model: weight / total_weight
                for model, weight in model_weights.items()
            }

            # Weighted random selection
            r = random.random()
            cumsum = 0
            for model, weight in normalized_weights.items():
                cumsum += weight
                if r <= cumsum:
                    return model

            return list(available_models)[0]

        except Exception as e:
            self._logger.error(f"Weighted random routing failed: {e}")
            return None

    def _calculate_weights(self,
                         models: Set[str],
                         model_load: Dict[str, float]) -> Dict[str, float]:
        """Calculate routing weights"""
        weights = {}
        for model in models:
            # Start with base weight
            weight = 1.0

            # Apply load penalty
            load = model_load.get(model, 0)
            weight *= (1 - load)

            weights[model] = max(0.1, weight)  # Ensure minimum weight

        return weights

    def _calculate_error_score(self, model: str) -> float:
        """Calculate error score for model"""
        try:
            requests = self.metrics.request_counts.get(model, 0)
            if requests == 0:
                return 0

            errors = self.metrics.error_counts.get(model, 0)
            error_rate = errors / requests

            # Exponential penalty for high error rates
            return min(1.0, error_rate * 2)

        except Exception as e:
            self._logger.error(f"Error score calculation failed: {e}")
            return 0

    def _calculate_response_score(self, model: str) -> float:
        """Calculate response time score"""
        try:
            times = self.metrics.response_times.get(model, [])
            if not times:
                return 0

            # Calculate statistics
            avg_time = statistics.mean(times)
            if avg_time == 0:
                return 0

            # Score based on inverse of average time
            # Normalize to [0, 0.5] range
            return min(0.5, 1 / avg_time)

        except Exception as e:
            self._logger.error(f"Response score calculation failed: {e}")
            return 0

    def record_request(self, model: str, duration: float, error: bool = False) -> None:
        """Record request metrics"""
        try:
            # Update request count
            self.metrics.request_counts[model] = (
                self.metrics.request_counts.get(model, 0) + 1
            )

            # Update error count
            if error:
                self.metrics.error_counts[model] = (
                    self.metrics.error_counts.get(model, 0) + 1
                )

            # Update response times
            times = self.metrics.response_times[model]
            times.append(duration)
            if len(times) > 100:  # Keep last 100 times
                times.pop(0)

            # Update last used
            self.metrics.last_used[model] = datetime.now(timezone.utc)

            # Process patterns
            asyncio.create_task(
                self._process_patterns(model, duration, error)
            )

            # Check circuit breaker
            if error:
                error_rate = self._calculate_error_score(model)
                if error_rate > 0.5:  # 50% error rate threshold
                    self._open_circuit(model)

        except Exception as e:
            self._logger.error(f"Failed to record request: {e}")

    def _open_circuit(self, model: str) -> None:
        """Open circuit breaker for model"""
        try:
            self.metrics.circuit_states[model] = "OPEN"
            self._logger.warning(f"Circuit opened for model: {model}")

            # Schedule circuit reset
            asyncio.create_task(self._reset_circuit(model))

        except Exception as e:
            self._logger.error(f"Failed to open circuit: {e}")

    async def _reset_circuit(self, model: str) -> None:
        """Reset circuit breaker after delay"""
        try:
            await asyncio.sleep(300)  # 5 minute timeout
            self.metrics.circuit_states[model] = "CLOSED"
            self._logger.info(f"Circuit reset for model: {model}")

        except Exception as e:
            self._logger.error(f"Failed to reset circuit: {e}")

    def get_model_metrics(self, model: str) -> Dict:
        """Get metrics for model"""
        try:
            metrics = {
                'requests': self.metrics.request_counts.get(model, 0),
                'errors': self.metrics.error_counts.get(model, 0),
                'circuit_state': self.metrics.circuit_states.get(model, "CLOSED"),
                'last_used': self.metrics.last_used.get(model),
                'patterns': []
            }

            # Calculate error rate
            if metrics['requests'] > 0:
                metrics['error_rate'] = metrics['errors'] / metrics['requests']
            else:
                metrics['error_rate'] = 0

            # Calculate response time stats
            times = self.metrics.response_times.get(model, [])
            if times:
                metrics['response_times'] = {
                    'mean': statistics.mean(times),
                    'median': statistics.median(times),
                    'std_dev': statistics.stdev(times) if len(times) > 1 else 0
                }

            # Add relevant patterns
            for pattern in self.metrics.patterns.values():
                if model in pattern.data.get('models', []):
                    metrics['patterns'].append({
                        'id': pattern.id,
                        'type': pattern.type,
                        'significance': pattern.significance,
                        'timestamp': pattern.timestamp
                    })

            return metrics

        except Exception as e:
            self._logger.error(f"Failed to get metrics: {e}")
            return {}
