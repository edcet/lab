"""Enhanced Shell Integration

This module implements an advanced shell integration system with AI capabilities,
pattern learning, and multi-provider LLM support.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
import time

from ..core.radical_store import RadicalStore
from ..core.components import PatternTracker, DataStore
from ..models.neural_network_manipulation import (
    NeuralManipulator, AIGatewayController
)

@dataclass
class ShellContext:
    """Shell execution context"""
    cwd: Path
    env: Dict[str, str]
    history: List[str]
    patterns: List[Dict]
    proficiency: Dict[str, float]

class EnhancedShell:
    """AI-powered shell integration"""

    def __init__(self, workspace_root: str = "."):
        # Core components
        self.store = RadicalStore(
            db_path=Path(workspace_root) / ".store" / "shell.db",
            evolution_config={"learning_rate": "adaptive"}
        )

        # Pattern tracking
        self.pattern_tracker = PatternTracker(
            storage_path=str(Path(workspace_root) / ".patterns"),
            analyzers={
                "command": CommandAnalyzer(),
                "workflow": WorkflowAnalyzer(),
                "context": ContextAnalyzer()
            }
        )

        # AI Integration
        self.neural_manipulator = NeuralManipulator()
        self.gateway_controller = AIGatewayController()

        # LLM Providers
        self.providers = {
            "ollama": {
                "endpoint": "http://localhost:11434",
                "models": ["codellama", "deepseek-coder", "neural-chat"],
                "specialties": ["code", "shell", "analysis"]
            },
            "lmstudio": {
                "endpoint": "http://localhost:1234",
                "models": ["deepthink-reasoning"],
                "specialties": ["reasoning", "planning"]
            },
            "tgpt": {
                "endpoint": "http://localhost:4891",
                "specialties": ["shell", "automation"]
            }
        }

        # Context tracking
        self.context = ShellContext(
            cwd=Path.cwd(),
            env={},
            history=[],
            patterns=[],
            proficiency={
                "command_mastery": 0.0,
                "workflow_efficiency": 0.0,
                "context_awareness": 0.0
            }
        )

        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize the enhanced shell"""
        try:
            # Initialize core components
            await self.store.initialize()
            await self.pattern_tracker.initialize()

            # Initialize AI providers
            for provider, config in self.providers.items():
                success = await self._init_provider(provider, config)
                if not success:
                    self.logger.warning(f"Failed to initialize {provider}")

            # Load initial context
            await self._load_context()

            return True

        except Exception as e:
            self.logger.error(f"Shell initialization failed: {e}")
            return False

    async def execute_command(self, command: str) -> Dict:
        """Execute command with AI enhancement"""
        start_time = time.time()

        try:
            # Update context
            self.context.history.append(command)

            # Analyze command patterns
            patterns = await self.pattern_tracker.analyze_command(command)

            # Get AI suggestions
            suggestions = await self._get_ai_suggestions(command, patterns)

            # Execute with monitoring
            result = await self._execute_with_learning(command, suggestions)

            # Track patterns
            await self._track_execution_patterns(command, result, time.time() - start_time)

            # Update proficiency
            self._update_proficiency(command, result)

            return result

        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return {"success": False, "error": str(e)}

    async def _init_provider(self, provider: str, config: Dict) -> bool:
        """Initialize an LLM provider"""
        try:
            if provider == "ollama":
                return await self.neural_manipulator.init_ollama(config)
            elif provider == "lmstudio":
                return await self.gateway_controller.init_lmstudio(config)
            elif provider == "tgpt":
                return await self._init_tgpt(config)
            return False
        except Exception as e:
            self.logger.error(f"Provider initialization failed: {e}")
            return False

    async def _get_ai_suggestions(self, command: str, patterns: List[Dict]) -> List[Dict]:
        """Get AI-powered command suggestions"""
        suggestions = []

        # Get suggestions from each provider
        for provider, config in self.providers.items():
            if await self._check_provider_status(provider):
                provider_suggestions = await self._get_provider_suggestions(
                    provider, command, patterns
                )
                suggestions.extend(provider_suggestions)

        return suggestions

    async def _execute_with_learning(self, command: str, suggestions: List[Dict]) -> Dict:
        """Execute command while learning patterns"""
        # Select best suggestion if available
        enhanced_command = await self._enhance_command(command, suggestions)

        # Execute with safety checks
        result = await self._safe_execute(enhanced_command)

        # Learn from execution
        await self._learn_from_execution(command, enhanced_command, result)

        return result

    async def _track_execution_patterns(self, command: str, result: Dict, duration: float):
        """Track command execution patterns"""
        pattern = {
            "command": command,
            "result": result,
            "duration": duration,
            "context": {
                "cwd": str(self.context.cwd),
                "history": self.context.history[-5:],  # Last 5 commands
                "proficiency": self.context.proficiency
            }
        }

        await self.store.store_pattern(pattern)
        await self.pattern_tracker.track_pattern(pattern)

    def _update_proficiency(self, command: str, result: Dict):
        """Update user proficiency metrics"""
        if result.get("success"):
            self.context.proficiency["command_mastery"] += 0.01
            if result.get("workflow_optimization"):
                self.context.proficiency["workflow_efficiency"] += 0.02
            if result.get("context_aware"):
                self.context.proficiency["context_awareness"] += 0.02
