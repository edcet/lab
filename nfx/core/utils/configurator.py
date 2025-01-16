"""NFX Configurator Module

Advanced configuration management for NFX with integrated AutoGPT functionality.
Includes model validation, overrides, and neural configuration.
"""
import asyncio
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from rich.console import Console
from rich.prompt import Confirm, Prompt

from nfx.core.config import NFXConfig
from nfx.core.models import ModelName, ModelProvider
from nfx.core.utils.telemetry import telemetry_manager

logger = logging.getLogger(__name__)
console = Console()

class ConfigurationLevel(str, Enum):
    """Configuration levels"""
    BASIC = "basic"  # Basic system configuration
    ENHANCED = "enhanced"  # + Performance tuning
    NEURAL = "neural"  # + Neural system config
    QUANTUM = "quantum"  # + Quantum system config
    WARFARE = "warfare"  # + Neural warfare config

@dataclass
class ConfigOverrides:
    """Configuration overrides"""
    continuous_mode: bool = False
    continuous_limit: Optional[int] = None
    skip_reprompt: bool = False
    skip_news: bool = False
    neural_enabled: bool = True
    quantum_enabled: bool = True
    warfare_enabled: bool = False
    debug_mode: bool = False
    log_level: str = "INFO"
    memory_size: int = 1024
    thread_count: int = 8
    process_count: int = 4

class ConfigurationManager:
    """Manages NFX configuration"""

    def __init__(
        self,
        config: NFXConfig,
        level: ConfigurationLevel = ConfigurationLevel.BASIC,
        config_dir: Optional[Path] = None
    ):
        """Initialize configuration manager

        Args:
            config: NFX configuration
            level: Configuration level
            config_dir: Optional config directory
        """
        self.config = config
        self.level = level
        self.config_dir = config_dir or Path.home() / ".nfx" / "config"
        self.overrides = ConfigOverrides()
        self._setup_config_dir()

    def _setup_config_dir(self) -> None:
        """Setup configuration directory"""
        if self.config_dir:
            self.config_dir.mkdir(parents=True, exist_ok=True)

    async def apply_overrides(
        self,
        continuous: bool = False,
        continuous_limit: Optional[int] = None,
        skip_reprompt: bool = False,
        skip_news: bool = False,
        neural_enabled: bool = True,
        quantum_enabled: bool = True,
        warfare_enabled: bool = False,
        debug_mode: bool = False,
        log_level: str = "INFO",
        memory_size: int = 1024,
        thread_count: int = 8,
        process_count: int = 4
    ) -> None:
        """Apply configuration overrides

        Args:
            continuous: Enable continuous mode
            continuous_limit: Limit for continuous mode
            skip_reprompt: Skip reprompting
            skip_news: Skip news display
            neural_enabled: Enable neural system
            quantum_enabled: Enable quantum system
            warfare_enabled: Enable warfare system
            debug_mode: Enable debug mode
            log_level: Logging level
            memory_size: Memory size in MB
            thread_count: Number of threads
            process_count: Number of processes
        """
        # Update overrides
        self.overrides = ConfigOverrides(
            continuous_mode=continuous,
            continuous_limit=continuous_limit,
            skip_reprompt=skip_reprompt,
            skip_news=skip_news,
            neural_enabled=neural_enabled,
            quantum_enabled=quantum_enabled,
            warfare_enabled=warfare_enabled,
            debug_mode=debug_mode,
            log_level=log_level,
            memory_size=memory_size,
            thread_count=thread_count,
            process_count=process_count
        )

        # Validate continuous mode
        if continuous:
            logger.warning(
                "Continuous mode is potentially dangerous and may cause unintended "
                "actions. Use with caution."
            )
            if not await Confirm.ask(
                "[bold red]Enable continuous mode?[/] This is potentially dangerous.",
                default=False
            ):
                self.overrides.continuous_mode = False
                self.overrides.continuous_limit = None

        # Validate warfare mode
        if warfare_enabled:
            logger.warning(
                "Neural warfare system is extremely powerful and potentially "
                "dangerous. Use with extreme caution."
            )
            if not await Confirm.ask(
                "[bold red]Enable neural warfare?[/] This is extremely dangerous.",
                default=False
            ):
                self.overrides.warfare_enabled = False

        # Apply overrides to config
        self.config.continuous_mode = self.overrides.continuous_mode
        self.config.continuous_limit = self.overrides.continuous_limit
        self.config.skip_reprompt = self.overrides.skip_reprompt
        self.config.skip_news = self.overrides.skip_news
        self.config.neural_enabled = self.overrides.neural_enabled
        self.config.quantum_enabled = self.overrides.quantum_enabled
        self.config.warfare_enabled = self.overrides.warfare_enabled
        self.config.debug_mode = self.overrides.debug_mode
        self.config.log_level = self.overrides.log_level
        self.config.memory_size = self.overrides.memory_size
        self.config.thread_count = self.overrides.thread_count
        self.config.process_count = self.overrides.process_count

        # Check models
        self.config.fast_llm, self.config.smart_llm = await self.check_models(
            (self.config.fast_llm, "fast_llm"),
            (self.config.smart_llm, "smart_llm")
        )

    async def check_models(
        self,
        *models: Tuple[ModelName, Literal["smart_llm", "fast_llm"]]
    ) -> Tuple[ModelName, ...]:
        """Check model availability

        Args:
            *models: Models to check

        Returns:
            Tuple of available models
        """
        checked_models: List[ModelName] = []

        for model, model_type in models:
            # Check each provider
            available = False
            for provider in ModelProvider:
                try:
                    # Try to validate model with provider
                    if await self._validate_model(provider, model):
                        available = True
                        checked_models.append(model)
                        break
                except Exception as e:
                    logger.debug(f"Error checking {model} with {provider}: {e}")

            if not available:
                # Fallback to default model
                logger.warning(
                    f"Model {model} not available. "
                    f"Falling back to default for {model_type}."
                )
                checked_models.append(self.config.default_model)

        return tuple(checked_models)

    async def _validate_model(
        self,
        provider: ModelProvider,
        model: ModelName
    ) -> bool:
        """Validate model with provider

        Args:
            provider: Model provider
            model: Model name

        Returns:
            True if model is available
        """
        # TODO: Implement model validation
        return True

    async def save(self) -> None:
        """Save configuration"""
        if not self.config_dir:
            return

        config_file = self.config_dir / "config.json"
        self.config.save(config_file)

    async def load(self) -> None:
        """Load configuration"""
        if not self.config_dir:
            return

        config_file = self.config_dir / "config.json"
        if config_file.exists():
            self.config.load(config_file)

    async def validate(self) -> None:
        """Validate configuration"""
        # Basic validation
        if self.config.memory_size < 128:
            raise ValueError("Memory size must be at least 128MB")

        if self.config.thread_count < 1:
            raise ValueError("Thread count must be at least 1")

        if self.config.process_count < 1:
            raise ValueError("Process count must be at least 1")

        # Level-specific validation
        if self.level >= ConfigurationLevel.NEURAL:
            if not self.config.neural_enabled:
                raise ValueError("Neural system required for neural configuration")

        if self.level >= ConfigurationLevel.QUANTUM:
            if not self.config.quantum_enabled:
                raise ValueError("Quantum system required for quantum configuration")

        if self.level >= ConfigurationLevel.WARFARE:
            if not self.config.warfare_enabled:
                raise ValueError("Warfare system required for warfare configuration")

        # Validate models
        await self.check_models(
            (self.config.fast_llm, "fast_llm"),
            (self.config.smart_llm, "smart_llm")
        )

# Global configuration manager
config_manager = ConfigurationManager(NFXConfig())
