"""Health Monitoring System for Core Components"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import psutil
import aiohttp
import sqlite3

@dataclass
class HealthMetrics:
    """System health metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    open_file_descriptors: int
    thread_count: int
    process_count: int
    timestamp: datetime

@dataclass
class ComponentHealth:
    """Individual component health status"""
    component_id: str
    status: str  # healthy, degraded, unhealthy
    last_check: datetime
    response_time: float
    error_count: int
    warning_count: int
    metrics: Dict[str, float]
    details: Optional[str] = None

@dataclass
class AlertConfig:
    """Alert configuration"""
    cpu_threshold: float = 80.0
    memory_threshold: float = 80.0
    disk_threshold: float = 85.0
    response_time_threshold: float = 2.0
    error_threshold: int = 5
    warning_threshold: int = 10
    check_interval: int = 60  # seconds
    alert_cooldown: int = 300  # seconds

class HealthMonitor:
    """Core health monitoring system"""

    def __init__(self, config_path: str = "~/.config/health"):
        self.config_path = Path(config_path).expanduser()
        self.config_path.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self.db_path = self.config_path / "health.db"
        self._setup_database()

        # Component registry
        self.components: Dict[str, Dict[str, Any]] = {}
        self.endpoints: Dict[str, str] = {}

        # Alert tracking
        self.alert_history: Dict[str, datetime] = {}
        self.alert_config = AlertConfig()

        # Monitoring state
        self.is_monitoring = False
        self.background_tasks: Set[asyncio.Task] = set()

        # Setup logging
        self._setup_logging()

    def _setup_database(self):
        """Initialize SQLite database for health metrics"""
        with sqlite3.connect(self.db_path) as conn:
            # System metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    cpu_percent REAL NOT NULL,
                    memory_percent REAL NOT NULL,
                    disk_usage_percent REAL NOT NULL,
                    open_file_descriptors INTEGER NOT NULL,
                    thread_count INTEGER NOT NULL,
                    process_count INTEGER NOT NULL
                )
            """)

            # Component health table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS component_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    response_time REAL NOT NULL,
                    error_count INTEGER NOT NULL,
                    warning_count INTEGER NOT NULL,
                    metrics TEXT NOT NULL,
                    details TEXT
                )
            """)

            # Alert history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    component_id TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metrics TEXT NOT NULL
                )
            """)

    def _setup_logging(self):
        """Configure logging for health monitoring"""
        log_path = self.config_path / "health.log"
        logging.basicConfig(
            filename=str(log_path),
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("HealthMonitor")

    def register_component(
        self, component_id: str, endpoint: Optional[str] = None,
        check_method: Optional[callable] = None
    ):
        """Register a component for health monitoring"""
        self.components[component_id] = {
            "endpoint": endpoint,
            "check_method": check_method,
            "last_check": None,
            "status": "unknown"
        }
        if endpoint:
            self.endpoints[component_id] = endpoint
        self.logger.info(f"Registered component: {component_id}")

    async def start_monitoring(self):
        """Start health monitoring"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.logger.info("Starting health monitoring")

        # Start monitoring tasks
        loop = asyncio.get_event_loop()
        self.background_tasks.add(
            loop.create_task(self._system_metrics_loop())
        )
        self.background_tasks.add(
            loop.create_task(self._component_health_loop())
        )
        self.background_tasks.add(
            loop.create_task(self._alert_check_loop())
        )

    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.is_monitoring = False
        self.logger.info("Stopping health monitoring")

        # Cancel all background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()

    async def _system_metrics_loop(self):
        """Collect system metrics periodically"""
        while self.is_monitoring:
            try:
                metrics = self._collect_system_metrics()
                self._store_system_metrics(metrics)

                # Check for alerts
                await self._check_system_alerts(metrics)

                await asyncio.sleep(self.alert_config.check_interval)
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(10)  # Back off on error

    def _collect_system_metrics(self) -> HealthMetrics:
        """Collect current system metrics"""
        process = psutil.Process()

        return HealthMetrics(
            cpu_percent=psutil.cpu_percent(),
            memory_percent=psutil.virtual_memory().percent,
            disk_usage_percent=psutil.disk_usage('/').percent,
            open_file_descriptors=process.num_fds(),
            thread_count=process.num_threads(),
            process_count=len(psutil.pids()),
            timestamp=datetime.now()
        )

    def _store_system_metrics(self, metrics: HealthMetrics):
        """Store system metrics in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO system_metrics
                (timestamp, cpu_percent, memory_percent, disk_usage_percent,
                open_file_descriptors, thread_count, process_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.timestamp, metrics.cpu_percent, metrics.memory_percent,
                metrics.disk_usage_percent, metrics.open_file_descriptors,
                metrics.thread_count, metrics.process_count
            ))

    async def _component_health_loop(self):
        """Check component health periodically"""
        async with aiohttp.ClientSession() as session:
            while self.is_monitoring:
                try:
                    for component_id, info in self.components.items():
                        health = await self._check_component_health(
                            component_id, info, session
                        )
                        self._store_component_health(health)

                        # Check for alerts
                        await self._check_component_alerts(health)

                    await asyncio.sleep(self.alert_config.check_interval)
                except Exception as e:
                    self.logger.error(f"Error checking component health: {e}")
                    await asyncio.sleep(10)

    async def _check_component_health(
        self, component_id: str, info: Dict[str, Any],
        session: aiohttp.ClientSession
    ) -> ComponentHealth:
        """Check health of a specific component"""
        start_time = time.time()
        status = "healthy"
        error_count = 0
        warning_count = 0
        details = None
        metrics = {}

        try:
            if info["endpoint"]:
                # Check endpoint health
                async with session.get(info["endpoint"]) as response:
                    if response.status != 200:
                        status = "unhealthy"
                        error_count += 1
                        details = f"Endpoint returned status {response.status}"
                    metrics = await response.json()

            elif info["check_method"]:
                # Run custom health check
                check_result = await info["check_method"]()
                metrics = check_result.get("metrics", {})
                if not check_result.get("healthy", True):
                    status = "unhealthy"
                    error_count += 1
                    details = check_result.get("details")

        except Exception as e:
            status = "unhealthy"
            error_count += 1
            details = str(e)

        response_time = time.time() - start_time

        return ComponentHealth(
            component_id=component_id,
            status=status,
            last_check=datetime.now(),
            response_time=response_time,
            error_count=error_count,
            warning_count=warning_count,
            metrics=metrics,
            details=details
        )

    def _store_component_health(self, health: ComponentHealth):
        """Store component health in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO component_health
                (component_id, timestamp, status, response_time,
                error_count, warning_count, metrics, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                health.component_id, health.last_check, health.status,
                health.response_time, health.error_count, health.warning_count,
                json.dumps(health.metrics), health.details
            ))

    async def _alert_check_loop(self):
        """Check for and handle alerts periodically"""
        while self.is_monitoring:
            try:
                # Get latest metrics
                metrics = self._collect_system_metrics()
                await self._check_system_alerts(metrics)

                # Check component alerts
                for component_id in self.components:
                    alerts = await self._get_component_alerts(component_id)
                    for alert in alerts:
                        await self._handle_alert(alert)

                await asyncio.sleep(self.alert_config.check_interval)
            except Exception as e:
                self.logger.error(f"Error in alert check loop: {e}")
                await asyncio.sleep(10)

    async def _check_system_alerts(self, metrics: HealthMetrics):
        """Check system metrics for alert conditions"""
        alerts = []

        # CPU usage alert
        if metrics.cpu_percent > self.alert_config.cpu_threshold:
            alerts.append({
                "type": "system",
                "severity": "warning",
                "message": f"High CPU usage: {metrics.cpu_percent}%",
                "metrics": asdict(metrics)
            })

        # Memory usage alert
        if metrics.memory_percent > self.alert_config.memory_threshold:
            alerts.append({
                "type": "system",
                "severity": "warning",
                "message": f"High memory usage: {metrics.memory_percent}%",
                "metrics": asdict(metrics)
            })

        # Disk usage alert
        if metrics.disk_usage_percent > self.alert_config.disk_threshold:
            alerts.append({
                "type": "system",
                "severity": "warning",
                "message": f"High disk usage: {metrics.disk_usage_percent}%",
                "metrics": asdict(metrics)
            })

        # Handle alerts
        for alert in alerts:
            await self._handle_alert(alert)

    async def _check_component_alerts(self, health: ComponentHealth):
        """Check component health for alert conditions"""
        alerts = []

        # Response time alert
        if health.response_time > self.alert_config.response_time_threshold:
            alerts.append({
                "type": "component",
                "component_id": health.component_id,
                "severity": "warning",
                "message": f"Slow response time: {health.response_time:.2f}s",
                "metrics": asdict(health)
            })

        # Error count alert
        if health.error_count > self.alert_config.error_threshold:
            alerts.append({
                "type": "component",
                "component_id": health.component_id,
                "severity": "error",
                "message": f"High error count: {health.error_count}",
                "metrics": asdict(health)
            })

        # Handle alerts
        for alert in alerts:
            await self._handle_alert(alert)

    async def _handle_alert(self, alert: Dict[str, Any]):
        """Handle and store an alert"""
        # Check alert cooldown
        alert_key = f"{alert['type']}:{alert.get('component_id', 'system')}"
        last_alert = self.alert_history.get(alert_key)

        if last_alert and (datetime.now() - last_alert).total_seconds() < self.alert_config.alert_cooldown:
            return

        # Update alert history
        self.alert_history[alert_key] = datetime.now()

        # Store alert
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alert_history
                (timestamp, component_id, alert_type, severity, message, metrics)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(),
                alert.get("component_id", "system"),
                alert["type"],
                alert["severity"],
                alert["message"],
                json.dumps(alert["metrics"])
            ))

        # Log alert
        log_level = logging.ERROR if alert["severity"] == "error" else logging.WARNING
        self.logger.log(log_level, f"Alert: {alert['message']}")

    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status"""
        metrics = self._collect_system_metrics()

        component_status = {}
        for component_id, info in self.components.items():
            component_status[component_id] = {
                "status": info["status"],
                "last_check": info["last_check"]
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "system_metrics": asdict(metrics),
            "components": component_status,
            "alert_count": len(self.alert_history)
        }

    async def get_component_health(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Get health status for a specific component"""
        if component_id not in self.components:
            return None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM component_health
                WHERE component_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (component_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "component_id": row[1],
                "timestamp": row[2],
                "status": row[3],
                "response_time": row[4],
                "error_count": row[5],
                "warning_count": row[6],
                "metrics": json.loads(row[7]),
                "details": row[8]
            }

    async def get_alerts(
        self, component_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent alerts with optional filtering"""
        query = "SELECT * FROM alert_history"
        params = []

        where_clauses = []
        if component_id:
            where_clauses.append("component_id = ?")
            params.append(component_id)

        if severity:
            where_clauses.append("severity = ?")
            params.append(severity)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)

            alerts = []
            for row in cursor:
                alerts.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "component_id": row[2],
                    "alert_type": row[3],
                    "severity": row[4],
                    "message": row[5],
                    "metrics": json.loads(row[6])
                })

            return alerts

    async def cleanup_old_data(self, days: int = 30):
        """Clean up old monitoring data"""
        cleanup_before = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            # Clean up old metrics
            conn.execute(
                "DELETE FROM system_metrics WHERE timestamp < ?",
                (cleanup_before,)
            )

            # Clean up old health records
            conn.execute(
                "DELETE FROM component_health WHERE timestamp < ?",
                (cleanup_before,)
            )

            # Clean up old alerts
            conn.execute(
                "DELETE FROM alert_history WHERE timestamp < ?",
                (cleanup_before,)
            )
