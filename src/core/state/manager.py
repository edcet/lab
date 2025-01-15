"""Unified State Management System

This module implements a comprehensive state management system that consolidates:
- Core state tracking and persistence
- System monitoring and resource tracking
- Event handling and propagation
- Component orchestration
- Pattern detection and analysis
- Health monitoring and alerts
"""

import asyncio
import aiohttp
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time
import json
from pathlib import Path
import logging
from rich.console import Console

# Core State Models
@dataclass
class SystemResources:
    """System resource metrics"""
    memory_usage: Dict[str, float]
    cpu_usage: Dict[str, float]
    disk_usage: Dict[str, float]
    network_stats: Dict[str, Dict]

@dataclass
class ComponentState:
    """Individual component state"""
    status: str
    health: float
    last_update: datetime
    metrics: Dict[str, Any]
    error_count: int = 0
    warning_count: int = 0

@dataclass
class StateSnapshot:
    """Complete system state snapshot"""
    timestamp: datetime
    resources: SystemResources
    components: Dict[str, ComponentState]
    active_models: Set[str]
    task_queue: List[Dict]
    patterns: List[Dict]
    metadata: Dict = field(default_factory=dict)

@dataclass
class StateConfig:
    """Unified state configuration"""
    persistence_path: Path
    auto_save: bool = True
    save_interval: int = 60
    max_history: int = 1000
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "memory": 0.9,  # 90% usage
        "cpu": 0.8,     # 80% usage
        "queue": 100,   # 100 tasks
        "error_rate": 0.1  # 10% errors
    })

class UnifiedStateManager:
    """Unified state management system"""

    def __init__(self, config: StateConfig):
        # Core components
        self.config = config
        self.console = Console()
        self.logger = logging.getLogger("state.manager")

        # State storage
        self.current_state: Optional[StateSnapshot] = None
        self.state_history: List[StateSnapshot] = []
        self.component_states: Dict[str, ComponentState] = {}

        # Event system
        self.event_handlers: Dict[str, Set[callable]] = {}
        self.event_history: List[Dict] = []

        # Pattern tracking
        self.patterns: Dict[str, List[Dict]] = {}
        self.pattern_weights: Dict[str, float] = {}

        # Monitoring
        self._monitoring_tasks: Set[asyncio.Task] = set()
        self._is_running = False

    async def start(self):
        """Start the unified state management system"""
        if self._is_running:
            return

        self._is_running = True
        self.logger.info("Starting unified state management system")

        try:
            # Initialize persistence
            await self._initialize_persistence()

            # Start monitoring tasks
            self._monitoring_tasks.update([
                asyncio.create_task(self._monitor_resources()),
                asyncio.create_task(self._monitor_components()),
                asyncio.create_task(self._monitor_patterns()),
                asyncio.create_task(self._auto_save_loop())
            ])

            # Emit startup event
            await self.emit_event("system_start", {
                "timestamp": datetime.now(),
                "config": self.config.__dict__
            })

        except Exception as e:
            self.logger.error(f"Failed to start state management: {e}")
            self._is_running = False
            raise

    async def stop(self):
        """Stop the unified state management system"""
        if not self._is_running:
            return

        self.logger.info("Stopping unified state management system")
        self._is_running = False

        # Cancel monitoring tasks
        for task in self._monitoring_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        self._monitoring_tasks.clear()

        # Save final state
        await self.save_state()

        # Emit shutdown event
        await self.emit_event("system_stop", {
            "timestamp": datetime.now(),
            "final_state": self.current_state.__dict__ if self.current_state else None
        })

    async def update_component_state(self, component: str, state: Dict):
        """Update state for a specific component"""
        try:
            component_state = ComponentState(
                status=state.get("status", "unknown"),
                health=state.get("health", 0.0),
                last_update=datetime.now(),
                metrics=state.get("metrics", {}),
                error_count=state.get("error_count", 0),
                warning_count=state.get("warning_count", 0)
            )

            self.component_states[component] = component_state

            # Update current state
            if self.current_state:
                self.current_state.components[component] = component_state

            # Emit state change event
            await self.emit_event("component_state_change", {
                "component": component,
                "state": component_state.__dict__
            })

            # Check for alerts
            await self._check_component_alerts(component, component_state)

        except Exception as e:
            self.logger.error(f"Failed to update component state: {e}")
            raise

    async def register_event_handler(self, event: str, handler: callable):
        """Register an event handler"""
        if event not in self.event_handlers:
            self.event_handlers[event] = set()
        self.event_handlers[event].add(handler)

    async def emit_event(self, event: str, data: Dict):
        """Emit an event to all registered handlers"""
        event_data = {
            "event": event,
            "data": data,
            "timestamp": datetime.now()
        }
        self.event_history.append(event_data)

        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    await handler(event_data)
                except Exception as e:
                    self.logger.error(f"Event handler error: {e}")

    async def get_state_history(self,
                              start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None) -> List[StateSnapshot]:
        """Get state history within the specified time range"""
        if not start_time and not end_time:
            return self.state_history

        filtered = []
        for state in self.state_history:
            if start_time and state.timestamp < start_time:
                continue
            if end_time and state.timestamp > end_time:
                continue
            filtered.append(state)

        return filtered

    async def _monitor_resources(self):
        """Monitor system resources"""
        while self._is_running:
            try:
                resources = SystemResources(
                    memory_usage=await self._get_memory_usage(),
                    cpu_usage=await self._get_cpu_usage(),
                    disk_usage=await self._get_disk_usage(),
                    network_stats=await self._get_network_stats()
                )

                # Update current state
                if self.current_state:
                    self.current_state.resources = resources

                # Check resource alerts
                await self._check_resource_alerts(resources)

                await asyncio.sleep(1)  # Resource check interval

            except Exception as e:
                self.logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(5)  # Back off on error

    async def _monitor_components(self):
        """Monitor registered components"""
        while self._is_running:
            try:
                # Create new state snapshot
                snapshot = StateSnapshot(
                    timestamp=datetime.now(),
                    resources=self.current_state.resources if self.current_state else None,
                    components=self.component_states.copy(),
                    active_models=await self._get_active_models(),
                    task_queue=await self._get_task_queue(),
                    patterns=list(self.patterns.values())
                )

                # Update state
                self.current_state = snapshot
                self.state_history.append(snapshot)

                # Trim history if needed
                if len(self.state_history) > self.config.max_history:
                    self.state_history = self.state_history[-self.config.max_history:]

                await asyncio.sleep(1)  # Component check interval

            except Exception as e:
                self.logger.error(f"Component monitoring error: {e}")
                await asyncio.sleep(5)

    async def _monitor_patterns(self):
        """Monitor and analyze patterns"""
        while self._is_running:
            try:
                # Analyze current patterns
                for pattern_type, patterns in self.patterns.items():
                    weight = self.pattern_weights.get(pattern_type, 1.0)

                    # Update pattern scores
                    for pattern in patterns:
                        pattern["score"] = pattern.get("base_score", 0.5) * weight

                await asyncio.sleep(5)  # Pattern analysis interval

            except Exception as e:
                self.logger.error(f"Pattern monitoring error: {e}")
                await asyncio.sleep(5)

    async def _initialize_persistence(self):
        """Initialize state persistence"""
        self.config.persistence_path.parent.mkdir(parents=True, exist_ok=True)

        if self.config.persistence_path.exists():
            try:
                # Load existing state
                async with aiofiles.open(self.config.persistence_path) as f:
                    data = json.loads(await f.read())

                # Reconstruct state objects
                self.component_states = {
                    k: ComponentState(**v) for k, v in data.get("components", {}).items()
                }
                self.patterns = data.get("patterns", {})
                self.pattern_weights = data.get("pattern_weights", {})

                self.logger.info("Loaded existing state")

            except Exception as e:
                self.logger.error(f"Failed to load existing state: {e}")

    async def _auto_save_loop(self):
        """Automatic state saving loop"""
        while self._is_running and self.config.auto_save:
            try:
                await self.save_state()
                await asyncio.sleep(self.config.save_interval)
            except Exception as e:
                self.logger.error(f"Auto-save error: {e}")
                await asyncio.sleep(5)

    async def save_state(self):
        """Save current state to disk"""
        if not self.current_state:
            return

        try:
            state_data = {
                "timestamp": self.current_state.timestamp.isoformat(),
                "components": {
                    k: v.__dict__ for k, v in self.component_states.items()
                },
                "patterns": self.patterns,
                "pattern_weights": self.pattern_weights,
                "metadata": self.current_state.metadata
            }

            async with aiofiles.open(self.config.persistence_path, "w") as f:
                await f.write(json.dumps(state_data, indent=2))

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            raise

    async def _check_resource_alerts(self, resources: SystemResources):
        """Check for resource usage alerts"""
        alerts = []

        # Check memory usage
        if any(usage > self.config.alert_thresholds["memory"]
               for usage in resources.memory_usage.values()):
            alerts.append("High memory usage detected")

        # Check CPU usage
        if any(usage > self.config.alert_thresholds["cpu"]
               for usage in resources.cpu_usage.values()):
            alerts.append("High CPU usage detected")

        # Emit alerts
        for alert in alerts:
            await self.emit_event("resource_alert", {
                "type": "resource",
                "message": alert,
                "resources": resources.__dict__
            })

    async def _check_component_alerts(self, component: str, state: ComponentState):
        """Check for component-specific alerts"""
        alerts = []

        # Check health
        if state.health < 0.5:
            alerts.append(f"Low health detected for {component}")

        # Check error rate
        if state.error_count > 0:
            error_rate = state.error_count / (state.error_count + state.warning_count + 1)
            if error_rate > self.config.alert_thresholds["error_rate"]:
                alerts.append(f"High error rate detected for {component}")

        # Emit alerts
        for alert in alerts:
            await self.emit_event("component_alert", {
                "type": "component",
                "component": component,
                "message": alert,
                "state": state.__dict__
            })

    # Resource monitoring helpers
    async def _get_memory_usage(self) -> Dict[str, float]:
        """Get system memory usage"""
        # Implementation depends on system
        return {}

    async def _get_cpu_usage(self) -> Dict[str, float]:
        """Get CPU usage"""
        # Implementation depends on system
        return {}

    async def _get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage"""
        # Implementation depends on system
        return {}

    async def _get_network_stats(self) -> Dict[str, Dict]:
        """Get network statistics"""
        # Implementation depends on system
        return {}

    async def _get_active_models(self) -> Set[str]:
        """Get currently active models"""
        # Implementation depends on system
        return set()

    async def _get_task_queue(self) -> List[Dict]:
        """Get current task queue"""
        # Implementation depends on system
        return []
