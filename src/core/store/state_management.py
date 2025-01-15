"""State Management System

This module implements the unified state management system that handles:
- State tracking and persistence
- State transitions and validation
- Event handling and propagation
- Component orchestration
- Shutdown safety
"""

import asyncio
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
import time
import json
from pathlib import Path
import signal
import atexit

@dataclass
class StateConfig:
    """Configuration for state management"""
    persistence_path: Path
    auto_save: bool = True
    save_interval: int = 60
    max_history: int = 1000
    shutdown_timeout: float = 5.0  # Maximum time to wait for clean shutdown

@dataclass
class StateTransition:
    """Represents a state transition"""
    from_state: Dict[str, Any]
    to_state: Dict[str, Any]
    timestamp: float
    metadata: Optional[Dict] = None
    validated: bool = False

class StateManager:
    """Manages system state and orchestration"""

    def __init__(self, config: StateConfig):
        self.config = config
        self.current_state = {}
        self.state_history = []
        self.components = set()
        self.event_handlers = {}
        self._shutdown_flag = asyncio.Event()
        self._state_lock = asyncio.Lock()
        self._setup_persistence()
        self._setup_shutdown_handlers()

    def _setup_persistence(self):
        """Setup state persistence"""
        self.config.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        if self.config.persistence_path.exists():
            self._load_state()
        if self.config.auto_save:
            self._save_task = asyncio.create_task(self._auto_save_loop())

    def _setup_shutdown_handlers(self):
        """Setup handlers for graceful shutdown"""
        atexit.register(self._sync_shutdown)
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        asyncio.create_task(self._async_shutdown())

    async def _async_shutdown(self):
        """Asynchronous shutdown handler"""
        self._shutdown_flag.set()
        try:
            async with asyncio.timeout(self.config.shutdown_timeout):
                await self._save_state()
                await self._notify_components("shutdown")
        except asyncio.TimeoutError:
            print("Warning: Shutdown timeout exceeded")
        finally:
            if self._save_task and not self._save_task.done():
                self._save_task.cancel()

    def _sync_shutdown(self):
        """Synchronous shutdown handler for atexit"""
        if not self._shutdown_flag.is_set():
            asyncio.run(self._async_shutdown())

    async def _auto_save_loop(self):
        """Automatic state saving loop with safety checks"""
        while not self._shutdown_flag.is_set():
            try:
                async with self._state_lock:
                    await self._save_state()
                    await self._validate_state()
                await asyncio.sleep(self.config.save_interval)
            except Exception as e:
                print(f"Error in auto save loop: {e}")
                await asyncio.sleep(1)  # Brief pause before retry

    async def _save_state(self):
        """Save state with validation"""
        state_data = {
            "current_state": self.current_state,
            "history": self.state_history[-self.config.max_history:],
            "timestamp": time.time()
        }

        # Write to temporary file first
        temp_path = self.config.persistence_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w') as f:
                json.dump(state_data, f)
            # Atomic rename for safe persistence
            temp_path.rename(self.config.persistence_path)
        except Exception as e:
            print(f"Error saving state: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise

    async def _validate_state(self):
        """Validate current state integrity"""
        if not self.current_state:
            return True

        # Validate state transitions
        for transition in self.state_history[-10:]:  # Check recent transitions
            if not transition.validated:
                if not self._validate_transition(transition):
                    raise ValueError(f"Invalid state transition detected: {transition}")
                transition.validated = True

        return True

    def _validate_transition(self, transition: StateTransition) -> bool:
        """Validate a single state transition"""
        # Add validation logic here
        return True

    async def _notify_components(self, event: str):
        """Notify components of system events"""
        for component in self.components:
            if hasattr(component, f"on_{event}"):
                try:
                    await getattr(component, f"on_{event}")()
                except Exception as e:
                    print(f"Error notifying component {component} of {event}: {e}")

    def register_component(self, component: Any):
        """Register a component for state tracking"""
        self.components.add(component)
        self._update_state({
            "component_added": component.__class__.__name__,
            "timestamp": time.time()
        })

    def register_event_handler(self, event: str, handler: callable):
        """Register an event handler"""
        if event not in self.event_handlers:
            self.event_handlers[event] = set()
        self.event_handlers[event].add(handler)

    async def emit_event(self, event: str, data: Dict):
        """Emit an event to all registered handlers"""
        if event in self.event_handlers:
            await asyncio.gather(
                *[handler(data) for handler in self.event_handlers[event]]
            )

    def _update_state(self, update: Dict):
        """Update current state"""
        self.current_state.update(update)
        transition = StateTransition(
            from_state=self.current_state.copy(),
            to_state=update,
            timestamp=time.time()
        )
        self.state_history.append(transition)

        # Trim history if needed
        if len(self.state_history) > self.config.max_history:
            self.state_history = self.state_history[-self.config.max_history:]

    def _load_state(self):
        """Load state from disk"""
        try:
            with open(self.config.persistence_path) as f:
                state_data = json.load(f)

            self.current_state = state_data["current_state"]
            self.state_history = [
                StateTransition(
                    from_state=t["from"],
                    to_state=t["to"],
                    timestamp=t["timestamp"],
                    metadata=t.get("metadata")
                )
                for t in state_data["history"]
            ]
        except Exception as e:
            print(f"Error loading state: {e}")

    def get_component_state(self, component: Any) -> Dict:
        """Get state for a specific component"""
        return {
            k: v for k, v in self.current_state.items()
            if k.startswith(component.__class__.__name__)
        }

    def get_state_history(self, start_time: Optional[float] = None) -> List[StateTransition]:
        """Get state history, optionally filtered by start time"""
        if start_time is None:
            return self.state_history

        return [
            t for t in self.state_history
            if t.timestamp >= start_time
        ]

    async def rollback_to(self, timestamp: float):
        """Rollback state to a specific point in time"""
        target_state = None
        for transition in self.state_history:
            if transition.timestamp <= timestamp:
                target_state = transition.from_state

        if target_state is not None:
            self.current_state = target_state.copy()
            await self.emit_event("state_rollback", {
                "timestamp": timestamp,
                "new_state": self.current_state
            })
