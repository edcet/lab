"""NFX Configuration Module

Advanced configuration management for NFX with integrated AutoGPT functionality.
Handles application settings, agent control, model configuration, and credentials.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, SecretStr, ValidationInfo, field_validator

logger = logging.getLogger(__name__)

class ModelProvider(str, Enum):
    """Supported model providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    LM_STUDIO = "lm_studio"
    OLLAMA = "ollama"

class ModelName(str, Enum):
    """Available model names"""
    GPT4 = "gpt-4"
    GPT4_TURBO = "gpt-4-turbo-preview"
    GPT3 = "gpt-3.5-turbo"
    CLAUDE = "claude-3-opus"
    MIXTRAL = "mixtral-8x7b"
    LLAMA = "llama2-70b"

@dataclass
class LLMConfig:
    """Configuration for LLM providers"""
    provider: ModelProvider
    model: ModelName
    api_key: Optional[SecretStr] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    streaming: bool = True

@dataclass
class NFXConfig:
    """NFX Configuration"""

    # Application Settings
    project_root: Path = Path.cwd()
    app_data_dir: Path = field(default_factory=lambda: Path.cwd() / "data")
    log_dir: Path = field(default_factory=lambda: Path.cwd() / "logs")

    # Agent Settings
    agent_name: str = "NFX Agent"
    agent_role: str = "AI Assistant"
    agent_goals: List[str] = field(default_factory=list)
    continuous_mode: bool = False
    continuous_limit: int = 0

    # Model Configuration
    fast_llm: LLMConfig = field(default_factory=lambda: LLMConfig(
        provider=ModelProvider.OLLAMA,
        model=ModelName.MIXTRAL
    ))
    smart_llm: LLMConfig = field(default_factory=lambda: LLMConfig(
        provider=ModelProvider.LM_STUDIO,
        model=ModelName.LLAMA
    ))

    # Memory Settings
    memory_index: str = "nfx_memory"
    memory_backend: str = "faiss"
    max_memory_entries: int = 1000

    # Neural Settings
    neural_compute_threads: int = 8
    neural_compute_backend: str = "metal"
    quantum_enabled: bool = True
    reality_manipulation_level: int = 3

    # Security Settings
    restrict_to_workspace: bool = True
    disabled_commands: List[str] = field(default_factory=list)
    require_user_approval: bool = True

    def __post_init__(self):
        """Ensure directories exist"""
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

class ConfigBuilder:
    """Builds NFX configuration from environment and files"""

    @classmethod
    def from_env(cls) -> NFXConfig:
        """Build config from environment variables"""
        config = NFXConfig()

        # Load from env
        if project_root := os.getenv("NFX_PROJECT_ROOT"):
            config.project_root = Path(project_root)

        if agent_name := os.getenv("NFX_AGENT_NAME"):
            config.agent_name = agent_name

        if agent_role := os.getenv("NFX_AGENT_ROLE"):
            config.agent_role = agent_role

        if agent_goals := os.getenv("NFX_AGENT_GOALS"):
            config.agent_goals = agent_goals.split(",")

        if neural_threads := os.getenv("NFX_NEURAL_THREADS"):
            config.neural_compute_threads = int(neural_threads)

        # Load LLM configs
        for llm_type in ["fast_llm", "smart_llm"]:
            if provider := os.getenv(f"NFX_{llm_type.upper()}_PROVIDER"):
                getattr(config, llm_type).provider = ModelProvider(provider)

            if model := os.getenv(f"NFX_{llm_type.upper()}_MODEL"):
                getattr(config, llm_type).model = ModelName(model)

            if api_key := os.getenv(f"NFX_{llm_type.upper()}_API_KEY"):
                getattr(config, llm_type).api_key = SecretStr(api_key)

            if api_base := os.getenv(f"NFX_{llm_type.upper()}_API_BASE"):
                getattr(config, llm_type).api_base = api_base

        return config

    @classmethod
    def from_file(cls, config_file: Path) -> NFXConfig:
        """Load config from YAML file"""
        import yaml

        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        with open(config_file) as f:
            config_dict = yaml.safe_load(f)

        config = NFXConfig()

        # Update config from dict
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return config

async def validate_llm_configs(config: NFXConfig) -> None:
    """Validate LLM configurations and API keys"""

    for llm_config in [config.fast_llm, config.smart_llm]:
        if llm_config.provider == ModelProvider.OPENAI:
            # Validate OpenAI config
            if not llm_config.api_key:
                raise ValueError("OpenAI API key not configured")

            # Test API key
            import openai
            try:
                client = openai.Client(api_key=llm_config.api_key.get_secret_value())
                await client.models.list()
            except Exception as e:
                raise ValueError(f"Invalid OpenAI configuration: {e}")

        elif llm_config.provider == ModelProvider.ANTHROPIC:
            # Validate Anthropic config
            if not llm_config.api_key:
                raise ValueError("Anthropic API key not configured")

            if not re.match(r"^sk-ant-api03-[\w\-]{95}", llm_config.api_key.get_secret_value()):
                logger.warning("Potentially invalid Anthropic API key format")

        elif llm_config.provider == ModelProvider.GROQ:
            # Validate Groq config
            if not llm_config.api_key:
                raise ValueError("Groq API key not configured")

            # Test API key
            import groq
            try:
                client = groq.Client(api_key=llm_config.api_key.get_secret_value())
                await client.models.list()
            except Exception as e:
                raise ValueError(f"Invalid Groq configuration: {e}")

        elif llm_config.provider == ModelProvider.LM_STUDIO:
            # Validate LM Studio config
            if not llm_config.api_base:
                llm_config.api_base = "http://localhost:1234/v1"

        elif llm_config.provider == ModelProvider.OLLAMA:
            # Validate Ollama config
            if not llm_config.api_base:
                llm_config.api_base = "http://localhost:11434"
