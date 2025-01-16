"""Health Monitoring System

Handles health checks and monitoring for AI models and providers.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
from rich.console import Console

@dataclass
class HealthStatus:
    """Health status information"""
    is_healthy: bool
    last_check: datetime
    consecutive_failures: int
    error_message: Optional[str] = None
    latency: Optional[float] = None

@dataclass
class HealthConfig:
    """Health check configuration"""
    check_interval: int = 30  # seconds
    failure_threshold: int = 3
    timeout: float = 5.0  # seconds
    retry_interval: int = 60  # seconds for failed checks

class HealthMonitor:
    """Monitors health of AI models and providers"""

    def __init__(self, config: Optional[HealthConfig] = None):
        self.console = Console()
        self.config = config or HealthConfig()
        self.status: Dict[str, HealthStatus] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._running = False
        self._background_tasks: Set[asyncio.Task] = set()

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    async def start(self) -> None:
        """Start health monitoring"""
        if self._running:
            return

        self._running = True
        monitor_task = asyncio.create_task(self._monitor_loop())
        self._background_tasks.add(monitor_task)
        monitor_task.add_done_callback(self._background_tasks.discard)

    async def stop(self) -> None:
        """Stop health monitoring"""
        self._running = False
        for task in self._background_tasks:
            task.cancel()

        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

    def register_provider(self, provider_id: str, endpoint: str) -> None:
        """Register a provider for health monitoring"""
        if provider_id not in self.status:
            self.status[provider_id] = HealthStatus(
                is_healthy=True,
                last_check=datetime.min,
                consecutive_failures=0
            )
            logging.info(f"Registered provider {provider_id} for health monitoring")

    def register_callback(self, provider_id: str, callback: Callable) -> None:
        """Register a callback for health status changes"""
        if provider_id not in self._callbacks:
            self._callbacks[provider_id] = []
        self._callbacks[provider_id].append(callback)

    async def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            check_tasks = []
            now = datetime.now()

            for provider_id, status in self.status.items():
                # Check if it's time for next health check
                time_since_last = now - status.last_check
                check_interval = (
                    self.config.retry_interval
                    if not status.is_healthy
                    else self.config.check_interval
                )

                if time_since_last.total_seconds() >= check_interval:
                    check_tasks.append(self._check_provider(provider_id))

            if check_tasks:
                await asyncio.gather(*check_tasks, return_exceptions=True)

            await asyncio.sleep(1)  # Small sleep to prevent busy loop

    async def _check_provider(self, provider_id: str) -> None:
        """Check health of a specific provider"""
        status = self.status[provider_id]
        start_time = datetime.now()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{provider_id}/health",
                    timeout=self.config.timeout
                ) as response:
                    is_healthy = response.status == 200
                    latency = (datetime.now() - start_time).total_seconds()

                    await self._update_health_status(
                        provider_id,
                        is_healthy,
                        latency=latency
                    )

        except Exception as e:
            await self._update_health_status(
                provider_id,
                False,
                error_message=str(e)
            )

    async def _update_health_status(self,
                                  provider_id: str,
                                  is_healthy: bool,
                                  latency: Optional[float] = None,
                                  error_message: Optional[str] = None) -> None:
        """Update health status and trigger callbacks"""
        status = self.status[provider_id]
        old_health = status.is_healthy

        if is_healthy:
            status.consecutive_failures = 0
            status.error_message = None
        else:
            status.consecutive_failures += 1
            status.error_message = error_message

        # Update status
        status.is_healthy = (
            is_healthy and
            status.consecutive_failures < self.config.failure_threshold
        )
        status.last_check = datetime.now()
        status.latency = latency

        # Log status change
        if old_health != status.is_healthy:
            if status.is_healthy:
                logging.info(f"Provider {provider_id} is now healthy")
            else:
                logging.warning(
                    f"Provider {provider_id} is unhealthy: {error_message}"
                )

            # Trigger callbacks
            await self._trigger_callbacks(provider_id, status)

    async def _trigger_callbacks(self,
                               provider_id: str,
                               status: HealthStatus) -> None:
        """Trigger registered callbacks for a provider"""
        if provider_id in self._callbacks:
            for callback in self._callbacks[provider_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(provider_id, status)
                    else:
                        callback(provider_id, status)
                except Exception as e:
                    logging.error(
                        f"Error in health callback for {provider_id}: {e}"
                    )

    def get_status(self, provider_id: str) -> Optional[HealthStatus]:
        """Get current health status for a provider"""
        return self.status.get(provider_id)

    def get_all_status(self) -> Dict[str, HealthStatus]:
        """Get health status for all providers"""
        return self.status.copy()

    def is_healthy(self, provider_id: str) -> bool:
        """Check if a provider is currently healthy"""
        status = self.status.get(provider_id)
        return status.is_healthy if status else False
