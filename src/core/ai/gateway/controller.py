"""Unified Gateway Controller for Local AI Models"""

import asyncio
import aiohttp
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("gateway.controller")

@dataclass
class GatewayConfig:
    """Gateway configuration"""
    providers: Dict[str, Dict]
    routing_strategy: str = "adaptive"
    health_check_interval: int = 30
    metrics_enabled: bool = True

class UnifiedGatewayController:
    """Controls and manages local AI model interactions"""

    def __init__(self, config: GatewayConfig):
        self.config = config
        self.active_models = {}
        self.model_health = {}
        self.model_metrics = {}
        self._monitor_task = None

    async def initialize(self):
        """Initialize gateway and start monitoring"""
        try:
            # Start health monitoring
            self._monitor_task = asyncio.create_task(self._monitor_health())

            # Initialize connections to all providers
            for provider, config in self.config.providers.items():
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{config['endpoint']}/health") as resp:
                            if resp.status == 200:
                                self.model_health[provider] = True
                                for model in config.get("models", []):
                                    self.active_models[model["name"]] = {
                                        "provider": provider,
                                        "capabilities": model["capabilities"],
                                        "status": "active"
                                    }
                            else:
                                self.model_health[provider] = False
                except Exception as e:
                    logger.error(f"Failed to initialize provider {provider}: {e}")
                    self.model_health[provider] = False

        except Exception as e:
            logger.error(f"Gateway initialization failed: {e}")
            raise

    async def process_pattern(self, pattern: Dict) -> Optional[Dict]:
        """Process a pattern through available models"""
        try:
            results = []

            # Get available models with pattern processing capability
            capable_models = [
                model for model, info in self.active_models.items()
                if "pattern_analysis" in info["capabilities"]
            ]

            # Process through each capable model
            for model in capable_models:
                try:
                    provider = self.active_models[model]["provider"]
                    endpoint = self.config.providers[provider]["endpoint"]

                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{endpoint}/generate",
                            json={
                                "model": model,
                                "prompt": f"Analyze pattern: {pattern}",
                                "stream": False
                            }
                        ) as resp:
                            if resp.status == 200:
                                result = await resp.json()
                                results.append(result)
                except Exception as e:
                    logger.error(f"Pattern processing failed for {model}: {e}")
                    continue

            # Combine results
            if results:
                return {
                    "patterns": results,
                    "timestamp": datetime.now().isoformat()
                }
            return None

        except Exception as e:
            logger.error(f"Pattern processing failed: {e}")
            return None

    async def route_request(self, prompt: str, context: Dict = None) -> Optional[Dict]:
        """Route a request to the most appropriate model"""
        try:
            # Select model based on context and capabilities
            selected_model = await self._select_model(context)
            if not selected_model:
                return None

            # Get provider info
            provider = self.active_models[selected_model]["provider"]
            endpoint = self.config.providers[provider]["endpoint"]

            # Send request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint}/generate",
                    json={
                        "model": selected_model,
                        "prompt": prompt,
                        "stream": False,
                        "context": context
                    }
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None

        except Exception as e:
            logger.error(f"Request routing failed: {e}")
            return None

    async def _select_model(self, context: Optional[Dict] = None) -> Optional[str]:
        """Select the most appropriate model based on context"""
        try:
            if not context:
                # Default to first available model
                return next(iter(self.active_models))

            # Check required capabilities
            required_capabilities = context.get("required_capabilities", [])
            capable_models = [
                model for model, info in self.active_models.items()
                if all(cap in info["capabilities"] for cap in required_capabilities)
            ]

            if not capable_models:
                return None

            # Select based on routing strategy
            if self.config.routing_strategy == "adaptive":
                # TODO: Implement more sophisticated selection
                return capable_models[0]

            return capable_models[0]

        except Exception as e:
            logger.error(f"Model selection failed: {e}")
            return None

    def _get_available_models(self) -> Set[str]:
        """Get set of currently available models"""
        return {
            model for model, info in self.active_models.items()
            if info["status"] == "active"
        }

    async def _check_agent_health(self, model: str) -> str:
        """Check health status of a model"""
        try:
            if model not in self.active_models:
                return "unknown"

            provider = self.active_models[model]["provider"]
            if not self.model_health.get(provider, False):
                return "offline"

            return self.active_models[model]["status"]

        except Exception as e:
            logger.error(f"Health check failed for {model}: {e}")
            return "error"

    async def _check_task_progress(self, model: str) -> float:
        """Check task progress for a model"""
        try:
            if model not in self.active_models:
                return 0.0

            provider = self.active_models[model]["provider"]
            if not self.model_health.get(provider, False):
                return 0.0

            # TODO: Implement actual progress tracking
            return 100.0 if self.active_models[model]["status"] == "active" else 0.0

        except Exception as e:
            logger.error(f"Progress check failed for {model}: {e}")
            return 0.0

    async def _monitor_health(self):
        """Monitor health of all providers"""
        while True:
            try:
                for provider, config in self.config.providers.items():
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                f"{config['endpoint']}/health",
                                timeout=5
                            ) as resp:
                                is_healthy = resp.status == 200
                                self.model_health[provider] = is_healthy

                                # Update model statuses
                                for model in config.get("models", []):
                                    if model["name"] in self.active_models:
                                        self.active_models[model["name"]]["status"] = \
                                            "active" if is_healthy else "offline"
                    except Exception as e:
                        logger.error(f"Health check failed for {provider}: {e}")
                        self.model_health[provider] = False

                await asyncio.sleep(self.config.health_check_interval)

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(5)  # Back off on error
