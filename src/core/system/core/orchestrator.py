"""Core system orchestrator implementation"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import logging
import time

@dataclass
class ComponentConfig:
    """Component configuration"""
    name: str
    enabled: bool = True
    parallel: bool = True
    dependencies: List[str] = None
    health_check: Optional[str] = None
    startup_timeout: int = 30
    retry_count: int = 3

class Orchestrator:
    """Core system orchestrator"""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.components: Dict[str, ComponentConfig] = {}
        self.running_components = {}
        self.component_tasks = {}
        self.event_handlers = {}
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize the orchestrator"""
        try:
            # Load component configurations
            config = self._load_config()

            for name, cfg in config.get("components", {}).items():
                self.components[name] = ComponentConfig(
                    name=name,
                    enabled=cfg.get("enabled", True),
                    parallel=cfg.get("parallel", True),
                    dependencies=cfg.get("dependencies", []),
                    health_check=cfg.get("health_check"),
                    startup_timeout=cfg.get("startup_timeout", 30),
                    retry_count=cfg.get("retry_count", 3)
                )

            self.logger.info(f"Loaded {len(self.components)} component configs")
            return True

        except Exception as e:
            self.logger.error(f"Orchestrator initialization failed: {e}")
            return False

    def _load_config(self) -> Dict:
        """Load orchestrator configuration"""
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}

    async def start(self):
        """Start orchestrated components"""
        try:
            # Build dependency graph
            dep_graph = self._build_dependency_graph()

            # Start components in dependency order
            for component_batch in dep_graph:
                if not component_batch:
                    continue

                # Start batch in parallel if enabled
                tasks = []
                for name in component_batch:
                    config = self.components[name]
                    if not config.enabled:
                        continue

                    if config.parallel:
                        task = asyncio.create_task(
                            self._start_component(name, config)
                        )
                        tasks.append(task)
                    else:
                        await self._start_component(name, config)

                if tasks:
                    await asyncio.gather(*tasks)

            self.logger.info("All components started successfully")

        except Exception as e:
            self.logger.error(f"Component startup failed: {e}")
            raise

    async def _start_component(self, name: str, config: ComponentConfig):
        """Start a single component"""
        for attempt in range(config.retry_count):
            try:
                # Get component instance
                component = self.running_components.get(name)
                if not component:
                    self.logger.error(f"Component {name} not found")
                    return

                # Start component
                started = await asyncio.wait_for(
                    component.start(),
                    timeout=config.startup_timeout
                )

                if started:
                    self.logger.info(f"Component {name} started successfully")

                    # Start health check if configured
                    if config.health_check:
                        self.component_tasks[name] = asyncio.create_task(
                            self._monitor_component(name, component)
                        )
                    return True

            except asyncio.TimeoutError:
                self.logger.warning(
                    f"Component {name} startup timed out, attempt {attempt + 1}"
                )
            except Exception as e:
                self.logger.error(
                    f"Component {name} startup failed: {e}, attempt {attempt + 1}"
                )

            # Wait before retry
            await asyncio.sleep(1)

        self.logger.error(f"Component {name} failed to start after {config.retry_count} attempts")
        return False

    def _build_dependency_graph(self) -> List[List[str]]:
        """Build component dependency graph"""
        graph = []
        remaining = set(self.components.keys())

        while remaining:
            # Find components with satisfied dependencies
            batch = set()
            for name in remaining:
                config = self.components[name]
                if not config.dependencies or all(
                    dep not in remaining for dep in config.dependencies
                ):
                    batch.add(name)

            if not batch:
                # Circular dependency
                self.logger.error(f"Circular dependency detected in: {remaining}")
                break

            graph.append(list(batch))
            remaining -= batch

        return graph

    async def _monitor_component(self, name: str, component):
        """Monitor component health"""
        while True:
            try:
                health = await component.health_check()
                if not health.get("healthy", False):
                    self.logger.warning(
                        f"Component {name} health check failed: {health.get('reason')}"
                    )

            except Exception as e:
                self.logger.error(f"Component {name} health check failed: {e}")

            await asyncio.sleep(30)

    async def stop(self):
        """Stop all components"""
        try:
            # Cancel monitoring tasks
            for task in self.component_tasks.values():
                task.cancel()

            # Stop components in reverse dependency order
            dep_graph = self._build_dependency_graph()
            for component_batch in reversed(dep_graph):
                if not component_batch:
                    continue

                # Stop batch in parallel
                tasks = []
                for name in component_batch:
                    component = self.running_components.get(name)
                    if component:
                        task = asyncio.create_task(component.stop())
                        tasks.append(task)

                if tasks:
                    await asyncio.gather(*tasks)

            self.logger.info("All components stopped successfully")

        except Exception as e:
            self.logger.error(f"Component shutdown failed: {e}")
            raise

    async def health_check(self) -> Dict:
        """Check orchestrator health"""
        return {
            "healthy": True,
            "components": {
                name: component.health_check()
                for name, component in self.running_components.items()
            }
        }

    def register_component(self, name: str, component, config: Optional[Dict] = None):
        """Register a component with the orchestrator"""
        if config:
            self.components[name] = ComponentConfig(name=name, **config)
        else:
            self.components[name] = ComponentConfig(name=name)

        self.running_components[name] = component
        self.logger.info(f"Registered component: {name}")

    def register_event_handler(self, event: str, handler: Callable):
        """Register an event handler"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)

    async def emit_event(self, event: str, data: Dict):
        """Emit an event to registered handlers"""
        handlers = self.event_handlers.get(event, [])
        for handler in handlers:
            try:
                await handler(data)
            except Exception as e:
                self.logger.error(f"Event handler failed: {e}")
