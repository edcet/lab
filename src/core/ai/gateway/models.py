"""Data models for AI gateway"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from datetime import datetime

@dataclass
class ModelCapabilities:
    """Model capabilities and specifications"""
    name: str
    provider: str
    capabilities: Set[str]
    context_window: int = 4096
    max_tokens: int = 4096
    supports_function_calling: bool = False
    supports_vision: bool = False
    temperature: float = 0.7

@dataclass
class ProviderConfig:
    """Provider configuration"""
    name: str
    endpoint: str
    models: List[Dict]
    timeout: float = 30.0
    retry_limit: int = 3
