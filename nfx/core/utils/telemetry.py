"""NFX Telemetry Module

Advanced telemetry for NFX with integrated AutoGPT functionality.
Includes performance tracking, error reporting, and neural activity monitoring.
"""
import asyncio
import json
import logging
import os
import platform
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import click
import psutil
import sentry_sdk
from rich.console import Console
from rich.prompt import Confirm

from nfx.core.utils.utils import (
    env_file_exists,
    get_git_user_email,
    set_env_config_value,
    vcs_state_diverges_from_master,
)

console = Console()
logger = logging.getLogger(__name__)

class TelemetryLevel(str, Enum):
    """Telemetry collection levels"""
    NONE = "none"  # No telemetry
    BASIC = "basic"  # Basic system info and errors
    ENHANCED = "enhanced"  # + Performance metrics
    NEURAL = "neural"  # + Neural activity
    QUANTUM = "quantum"  # + Quantum state

@dataclass
class SystemInfo:
    """System information for telemetry"""
    os: str
    python_version: str
    cpu_count: int
    total_memory: int
    git_email: Optional[str]
    environment: str

@dataclass
class PerformanceMetrics:
    """Performance metrics for telemetry"""
    cpu_percent: float
    memory_percent: float
    neural_throughput: float
    quantum_states: int
    operation_count: int
    timestamp: datetime

class TelemetryManager:
    """Manages telemetry collection and reporting"""

    def __init__(
        self,
        level: TelemetryLevel = TelemetryLevel.BASIC,
        sentry_dsn: Optional[str] = None,
        local_storage: Optional[Path] = None
    ):
        """Initialize telemetry manager

        Args:
            level: Telemetry collection level
            sentry_dsn: Optional Sentry DSN for error reporting
            local_storage: Optional path for local telemetry storage
        """
        self.level = level
        self.sentry_dsn = sentry_dsn
        self.local_storage = local_storage or Path.home() / ".nfx" / "telemetry"
        self.enabled = False
        self.system_info = self._collect_system_info()
        self._setup_storage()

    def _setup_storage(self) -> None:
        """Setup local storage for telemetry data"""
        if self.local_storage:
            self.local_storage.mkdir(parents=True, exist_ok=True)

    def _collect_system_info(self) -> SystemInfo:
        """Collect system information"""
        return SystemInfo(
            os=platform.platform(),
            python_version=sys.version,
            cpu_count=psutil.cpu_count(),
            total_memory=psutil.virtual_memory().total,
            git_email=get_git_user_email(),
            environment="production" if not vcs_state_diverges_from_master() else "dev"
        )

    def _collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect performance metrics"""
        return PerformanceMetrics(
            cpu_percent=psutil.cpu_percent(),
            memory_percent=psutil.virtual_memory().percent,
            neural_throughput=self._get_neural_throughput(),
            quantum_states=self._count_quantum_states(),
            operation_count=self._get_operation_count(),
            timestamp=datetime.now()
        )

    def _get_neural_throughput(self) -> float:
        """Get neural processing throughput"""
        # TODO: Implement neural throughput measurement
        return 0.0

    def _count_quantum_states(self) -> int:
        """Count active quantum states"""
        # TODO: Implement quantum state counting
        return 0

    def _get_operation_count(self) -> int:
        """Get total operation count"""
        # TODO: Implement operation counting
        return 0

    async def setup(self) -> None:
        """Setup telemetry collection"""
        if os.getenv("TELEMETRY_OPT_IN") is None:
            if not env_file_exists():
                return

            allow_telemetry = await console.input(
                "\n[bold]❓ Do you want to enable telemetry? ❓[/]\n"
                "This means NFX will send diagnostic data to help improve the system.\n"
                "It includes:\n"
                "- Basic system information\n"
                "- Error reports\n"
                "- Performance metrics\n"
                "- Neural activity data\n"
                "- Quantum state information\n\n"
                "Please enter 'yes' or 'no': "
            )

            enabled = allow_telemetry.lower() in ("y", "yes", "true")
            set_env_config_value("TELEMETRY_OPT_IN", "true" if enabled else "false")

            console.print(
                f"{'❤️  ' if enabled else '👍 '}Telemetry is "
                f"[{'green' if enabled else 'red'}]"
                f"{'enabled' if enabled else 'disabled'}[/]"
            )
            console.print(
                "💡 You can change this setting in .env with TELEMETRY_OPT_IN\n"
            )

        if os.getenv("TELEMETRY_OPT_IN", "").lower() == "true":
            self.enabled = True
            await self._setup_sentry()

    async def _setup_sentry(self) -> None:
        """Setup Sentry error reporting"""
        if not self.sentry_dsn:
            return

        sentry_sdk.init(
            dsn=self.sentry_dsn,
            enable_tracing=True,
            environment=self.system_info.environment
        )

        sentry_sdk.set_user({
            "email": self.system_info.git_email,
            "ip_address": "{{auto}}"
        })

    async def collect(self) -> None:
        """Collect telemetry data"""
        if not self.enabled:
            return

        metrics = self._collect_performance_metrics()

        # Store locally
        if self.local_storage:
            timestamp = metrics.timestamp.strftime("%Y%m%d_%H%M%S")
            metrics_file = self.local_storage / f"metrics_{timestamp}.json"

            metrics_data = {
                "system_info": vars(self.system_info),
                "metrics": vars(metrics)
            }

            with open(metrics_file, "w") as f:
                json.dump(metrics_data, f, default=str)

        # Send to Sentry if enabled
        if self.sentry_dsn:
            with sentry_sdk.push_scope() as scope:
                scope.set_context("metrics", vars(metrics))
                scope.set_context("system_info", vars(self.system_info))

    def capture_exception(self, error: Exception) -> None:
        """Capture and report an exception

        Args:
            error: Exception to report
        """
        if not self.enabled:
            return

        if self.sentry_dsn:
            sentry_sdk.capture_exception(error)

        logger.exception("Error captured by telemetry", exc_info=error)

    async def cleanup(self) -> None:
        """Cleanup telemetry resources"""
        if self.local_storage:
            # Cleanup old metrics files
            retention_days = 7
            cutoff = time.time() - (retention_days * 24 * 60 * 60)

            for metrics_file in self.local_storage.glob("metrics_*.json"):
                if metrics_file.stat().st_mtime < cutoff:
                    metrics_file.unlink()

# Global telemetry manager
telemetry_manager = TelemetryManager()
