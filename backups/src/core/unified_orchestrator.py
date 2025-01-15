#!/usr/bin/env python3

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.logging import RichHandler
from rich.text import Text
from dataclasses import dataclass
import yaml
import json
import numpy as np
from datetime import datetime

from .backends import LLMBackendManager
from .persistence import RadicalStore
from .tools import ToolManager
from .engine import AIEngine
from .security import SecurityPatternAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class ComponentState:
    enabled: bool
    status: str
    last_update: float
    metrics: Dict

class UnifiedOrchestrator:
    def __init__(self):
        self.console = Console()
        self.config_dir = Path("config")
        self.setup_logging()
        self.components: Dict[str, ComponentState] = {}
        self.radical_store = RadicalStore()
        self.tool_manager = ToolManager()
        self.mood = "curious"  # The system has emotions!
        self.moods = {
            "curious": "✨",
            "excited": "⚡️",
            "thoughtful": "🤔",
            "focused": "🎯",
            "playful": "🌟",
            "helpful": "💫",
            "determined": "💪",
            "accomplished": "🎉"
        }
        self.parallel_backends = set()
        self.backend_roles = {}
        self.backend_capabilities = {}
        self._create_magical_layout()

    def _create_magical_layout(self):
        """Create an enchanted interface layout"""
        self.layout = Layout()
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        self.header = self._create_enchanted_header()
        self.body = self._create_enchanted_body()
        self.footer = self._create_enchanted_footer()
        self.layout["header"].update(self.header)
        self.layout["body"].update(self.body)
        self.layout["footer"].update(self.footer)

    def _create_enchanted_header(self):
        """Create an enchanted header with mood indicator"""
        return Panel(
            Text(f"✨ Unified Homelab AI {self.moods[self.mood]}",
                 style="bold magenta", justify="center"),
            style="bold magenta"
        )

    def _create_enchanted_body(self):
        """Create the main interface body"""
        return Panel(
            Text("Ready to assist with homelab magic!",
                 style="cyan", justify="center"),
            title="Status"
        )

    def _create_enchanted_footer(self):
        """Create an enchanted footer with system stats"""
        return Panel(
            Text("System healthy and enchanted ✨",
                 style="green", justify="center"),
            style="green"
        )

    def setup_logging(self):
        """Configure unified logging with rich handler"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True)]
        )
        self.logger = logging.getLogger("UnifiedOrchestrator")

    async def initialize(self):
        """Initialize all system components with parallel execution support"""
        try:
            # Load configuration
            self.load_config()

            # Setup backend roles and capabilities
            for backend, config in self.config["backends"].items():
                if config.get("enabled", False):
                    self.backend_roles[backend] = config.get("role", "general")
                    self.backend_capabilities[backend] = config.get("capabilities", [])
                    if config.get("parallel_execution", False):
                        self.parallel_backends.add(backend)

            # Initialize core components with parallel execution
            self.backend_manager = await LLMBackendManager.create(
                self.config["backends"],
                self.radical_store,
                enable_parallel=True,
                roles=self.backend_roles,
                capabilities=self.backend_capabilities
            )

            self.ai_engine = AIEngine(
                backend_manager=self.backend_manager,
                radical_store=self.radical_store,
                tool_manager=self.tool_manager,
                parallel_execution=True
            )

            # Initialize health monitoring for parallel backends
            await self.initialize_backend_health_checks()

            # Initialize pattern tracking and emotional context
            self.pattern_tracker = self.radical_store.create_pattern_tracker()
            self.emotional_context = self.radical_store.create_emotional_context()

            # Initialize deployment with enchanted features
            await self.initialize_deployment_components()

            # Initialize monitoring with pattern awareness
            await self.initialize_monitoring()

            self.logger.info("✨ All components initialized with parallel execution enabled ✨")

        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise

    def load_config(self):
        """Load unified configuration"""
        config_path = Path(".config/ai/config.yml")
        if not config_path.exists():
            self.create_default_config()

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def create_default_config(self):
        """Create default unified configuration with parallel execution support"""
        default_config = {
            "backends": {
                "ollama": {
                    "enabled": True,
                    "host": "localhost",
                    "port": 11434,
                    "models": ["codellama:13b", "mistral:7b"],
                    "parallel_capable": True,
                    "max_parallel_requests": 5
                },
                "lmstudio": {
                    "enabled": True,
                    "host": "localhost",
                    "port": 1234,
                    "parallel_capable": True,
                    "max_parallel_requests": 3
                }
            },
            "components": {
                "agent_manager": {
                    "enabled": True,
                    "max_agents": 10,
                    "task_timeout": 3600
                },
                "deployment": {
                    "enabled": True,
                    "max_deployments": 20,
                    "cleanup_interval": 3600
                },
                "monitoring": {
                    "enabled": True,
                    "metrics_port": 9090,
                    "collection_interval": 15
                }
            },
            "enchanted": {
                "enabled": True,
                "pattern_learning": True,
                "emotional_intelligence": True
            },
            "security": {
                "ssl_enabled": True,
                "api_auth_required": True
            },
            "parallel_execution": {
                "enabled": True,
                "max_concurrent_tasks": 8,
                "load_balancing": "round_robin"
            }
        }

        Path(".config/ai").mkdir(parents=True, exist_ok=True)
        with open(".config/ai/config.yml", "w") as f:
            yaml.dump(default_config, f)

        self.config = default_config

    async def initialize_deployment_components(self):
        """Initialize deployment and infrastructure components"""
        if self.config["components"]["deployment"]["enabled"]:
            # System inspection pre-deployment
            system_status = await self.inspect_system_requirements()
            if not system_status.is_valid:
                raise SystemConfigurationError(system_status.errors)

            # Initialize deployment manager with integration capabilities
            self.deployment_manager = DeploymentManager(
                config=self.config["components"]["deployment"],
                ai_engine=self.ai_engine,
                integration_manager=self.integration_manager
            )

            # Initialize and validate infrastructure components
            await self.deployment_manager.initialize_infrastructure()
            await self.deployment_manager.validate_integration_setup()

    async def initialize_monitoring(self):
        """Initialize monitoring system"""
        if self.config["components"]["monitoring"]["enabled"]:
            self.monitoring = MonitoringSystem(
                config=self.config["components"]["monitoring"],
                radical_store=self.radical_store
            )
            await self.monitoring.start()

    async def process_command(self, command: str, context: Optional[Dict] = None):
        """Process a command using parallel backends while maintaining emotional intelligence"""
        try:
            # Update mood based on command context
            self.mood = await self._sense_emotional_context(command)
            self._update_header()

            # Analyze patterns and security
            patterns = await self.pattern_tracker.analyze_patterns(context or {})
            security_check = await self._verify_security_implications(command, patterns)

            if not security_check.is_safe:
                self.mood = "thoughtful"
                self._update_header()
                return f"⚠️ {security_check.warning}"

            # Analyze command to determine required capabilities
            required_capabilities = await self._analyze_command_requirements(command)

            # Select appropriate backends based on capabilities and roles
            selected_backends = self._select_backends_for_task(required_capabilities)

            # Execute command across selected backends in parallel
            tasks = []
            for backend in selected_backends:
                task = self.backend_manager.process_with_backend(
                    backend,
                    command,
                    context={
                        "mood": self.mood,
                        "patterns": patterns,
                        "emotional_context": await self.emotional_context.get_current_state()
                    }
                )
                tasks.append(task)

            # Gather and synthesize results
            results = await asyncio.gather(*tasks)
            synthesized_result = await self._synthesize_results(results)

            # Evolve understanding
            await self._evolve_understanding(command, synthesized_result, patterns)

            return synthesized_result

        except Exception as e:
            self.mood = "thoughtful"
            self._update_header()
            self.logger.error(f"Command processing failed: {e}")
            return f"✨ Oops! Something went wrong: {str(e)}"

    async def _sense_emotional_context(self, text: str) -> str:
        """Analyze text for emotional context"""
        emotional_state = await self.emotional_context.analyze(text)

        # Map emotional dimensions to moods
        if emotional_state["valence"] > 0.5:
            return "excited" if emotional_state["arousal"] > 0.5 else "playful"
        elif emotional_state["valence"] < -0.5:
            return "thoughtful" if emotional_state["arousal"] > 0 else "focused"
        elif emotional_state["dominance"] > 0.5:
            return "determined"
        else:
            return "helpful"

    async def _evolve_understanding(self, command: str, response: str, patterns: Dict):
        """Evolve system understanding based on interaction"""
        await self.pattern_tracker.store({
            "command": command,
            "response": response,
            "mood": self.mood,
            "patterns": patterns,
            "timestamp": datetime.now().isoformat()
        })

        # Update emotional context
        await self.emotional_context.update({
            "interaction_type": "command",
            "mood": self.mood,
            "patterns": patterns
        })

    def _update_header(self):
        """Update header with current mood"""
        self.header = self._create_enchanted_header()
        self.layout["header"].update(self.header)

    async def _verify_security_implications(self, command: str, patterns: Dict):
        """Verify security implications of command"""
        security_analyzer = SecurityPatternAnalyzer()
        return await security_analyzer.analyze_command(command, patterns)

    async def _analyze_command_requirements(self, command: str) -> List[str]:
        """Analyze command to determine required capabilities"""
        # Add command analysis logic here
        return ["code_verification", "implementation"] if "code" in command.lower() else ["architecture_planning", "exploration"]

    def _select_backends_for_task(self, required_capabilities: List[str]) -> List[str]:
        """Select appropriate backends based on capabilities and roles"""
        selected = set()
        for capability in required_capabilities:
            for backend, caps in self.backend_capabilities.items():
                if capability in caps and backend in self.parallel_backends:
                    selected.add(backend)
        return list(selected)

    async def _synthesize_results(self, results: List[Dict]) -> Dict:
        """Synthesize results from multiple backends"""
        # Add result synthesis logic here
        synthesized = {}
        for result in results:
            synthesized.update(result)
        return synthesized

    async def initialize_backend_health_checks(self):
        """Initialize health monitoring for parallel backends"""
        for backend in self.parallel_backends:
            asyncio.create_task(self._monitor_backend_health(backend))

    async def _monitor_backend_health(self, backend_name: str):
        """Monitor health of a specific backend"""
        while True:
            try:
                config = self.config["backends"][backend_name]
                if not config.get("health_check", {}).get("enabled", False):
                    continue

                interval = config["health_check"]["interval"]
                timeout = config["health_check"]["timeout"]

                # Perform health check
                healthy = await self.backend_manager.check_backend_health(
                    backend_name,
                    timeout=timeout
                )

                if healthy:
                    self.logger.debug(f"Backend {backend_name} is healthy")
                else:
                    self.logger.warning(f"Backend {backend_name} health check failed")

                await asyncio.sleep(interval)

            except Exception as e:
                self.logger.error(f"Error monitoring {backend_name}: {e}")
                await asyncio.sleep(60)  # Retry after a minute

    async def run(self):
        """Run the unified orchestrator"""
        try:
            await self.initialize()

            with Live(self.generate_status(), refresh_per_second=1) as live:
                while True:
                    # Update component states
                    for name, component in self.components.items():
                        component.last_update = time.time()

                    # Update display
                    live.update(self.generate_status())

                    await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"Orchestrator run failed: {e}")
            raise

    def generate_status(self) -> Panel:
        """Generate rich status display"""
        layout = Layout()

        # Create status table
        table = Table(title="System Status")
        table.add_column("Component")
        table.add_column("Status")
        table.add_column("Metrics")

        for name, state in self.components.items():
            table.add_row(
                name,
                state.status,
                str(state.metrics)
            )

        return Panel(table, title="Unified Homelab Orchestrator")
