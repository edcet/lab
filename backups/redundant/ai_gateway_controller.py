"""AI Gateway Controller

Manages AI model providers and routing.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ProviderInfo:
    """Information about an AI provider"""
    name: str
    endpoint: str
    models: List[str]
    capabilities: List[str]
    status: str = "active"
    last_check: Optional[float] = None

@dataclass
class Route:
    """Model routing information"""
    provider: str
    model: str
    capability: str
    confidence: float

class AIGatewayController:
    """Controls AI model providers and routing"""

    def __init__(self):
        self.initialized = False
        self.providers = {}
        self.routes = {}

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    async def initialize(self):
        """Initialize the gateway controller"""
        if self.initialized:
            return

        # Register default providers
        await self._register_default_providers()

        # Initialize routing table
        await self._initialize_routing()

        self.initialized = True
        logging.info("AI Gateway Controller initialized")

    async def _register_default_providers(self):
        """Register default AI providers"""
        default_providers = {
            "codellama": ProviderInfo(
                name="codellama",
                endpoint="http://localhost:11434",
                models=["codellama"],
                capabilities=["code_generation", "code_analysis"]
            ),
            "mixtral": ProviderInfo(
                name="mixtral",
                endpoint="http://localhost:1234",
                models=["mixtral"],
                capabilities=["text_generation", "analysis"]
            ),
            "gpt4": ProviderInfo(
                name="gpt4",
                endpoint="http://localhost:4891",
                models=["gpt4"],
                capabilities=["code_generation", "text_generation"]
            )
        }

        self.providers.update(default_providers)
        logging.info(f"Registered {len(default_providers)} default providers")

    async def _initialize_routing(self):
        """Initialize the routing table"""
        self.routes = {
            "code_generation": [
                Route("codellama", "codellama", "code_generation", 0.9),
                Route("gpt4", "gpt4", "code_generation", 0.8)
            ],
            "text_generation": [
                Route("mixtral", "mixtral", "text_generation", 0.9),
                Route("gpt4", "gpt4", "text_generation", 0.8)
            ],
            "analysis": [
                Route("mixtral", "mixtral", "analysis", 0.9)
            ]
        }

    async def list_providers(self) -> List[str]:
        """List available providers"""
        if not self.initialized:
            await self.initialize()
        return list(self.providers.keys())

    async def get_optimal_route(self, capability: str) -> Optional[Dict]:
        """Get optimal route for a capability"""
        if not self.initialized:
            await self.initialize()

        if capability not in self.routes:
            logging.warning(f"No routes found for capability: {capability}")
            return None

        # Get highest confidence route
        routes = self.routes[capability]
        optimal = max(routes, key=lambda r: r.confidence)

        return {
            "provider": optimal.provider,
            "model": optimal.model,
            "confidence": optimal.confidence
        }
