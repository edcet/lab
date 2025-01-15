"""System Monitoring with health checks and performance metrics"""

import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
import logging
from dataclasses import dataclass
import psutil
import numpy as np
from collections import defaultdict
import aiohttp
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import time

@dataclass
class HealthStatus:
    """System health status"""
    healthy: bool
    components: Dict[str, bool]
    issues: List[str]
    last_check: datetime
    metrics: Dict[str, float]

class SystemMonitor:
    """Comprehensive system monitoring"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.console = Console()
        
        # Component health status
        self.health_checks = defaultdict(bool)
        self.component_metrics = defaultdict(dict)
        self.error_counts = defaultdict(int)
        
        # Performance metrics
        self.metrics_history = defaultdict(list)
        self.latency_tracker = defaultdict(list)
        
        # Resource monitoring
        self.resource_usage = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'network': []
        }
        
        # Alert configuration
        self.alert_thresholds = {
            'error_rate': 0.1,      # 10% error rate
            'latency': 5.0,         # 5 seconds
            'cpu_usage': 0.8,       # 80% CPU
            'memory_usage': 0.85,   # 85% memory
            'disk_usage': 0.9       # 90% disk
        }
        
        # Status tracking
        self.status_history = []
        self.active = False

    async def initialize(self) -> bool:
        """Initialize monitoring system"""
        try:
            self.active = True
            
            # Start monitoring tasks
            asyncio.create_task(self._monitor_resources())
            asyncio.create_task(self._monitor_components())
            asyncio.create_task(self._monitor_performance())
            asyncio.create_task(self._check_alerts())
            
            self.logger.info("System Monitor initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Monitor initialization failed: {e}")
            return False

    async def check_health(self) -> HealthStatus:
        """Check system health status"""
        try:
            components = dict(self.health_checks)
            issues = []
            metrics = {}
            
            # Check component health
            for component, healthy in components.items():
                if not healthy:
                    issues.append(f"Component {component} is unhealthy")
            
            # Check error rates
            for component, count in self.error_counts.items():
                if count > 0:
                    total_ops = len(self.metrics_history[component])
                    error_rate = count / max(1, total_ops)
                    metrics[f"{component}_error_rate"] = error_rate
                    
                    if error_rate > self.alert_thresholds['error_rate']:
                        issues.append(
                            f"High error rate for {component}: {error_rate:.2%}"
                        )
            
            # Check resource usage
            cpu_usage = np.mean(self.resource_usage['cpu'][-10:]) if self.resource_usage['cpu'] else 0
            memory_usage = np.mean(self.resource_usage['memory'][-10:]) if self.resource_usage['memory'] else 0
            
            metrics.update({
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage
            })
            
            if cpu_usage > self.alert_thresholds['cpu_usage']:
                issues.append(f"High CPU usage: {cpu_usage:.2%}")
            if memory_usage > self.alert_thresholds['memory_usage']:
                issues.append(f"High memory usage: {memory_usage:.2%}")
            
            # Overall health status
            healthy = len(issues) == 0
            
            status = HealthStatus(
                healthy=healthy,
                components=components,
                issues=issues,
                last_check=datetime.now(),
                metrics=metrics
            )
            
            self.status_history.append(status)
            if len(self.status_history) > 1000:
                self.status_history = self.status_history[-1000:]
            
            return status
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return HealthStatus(
                healthy=False,
                components={},
                issues=[str(e)],
                last_check=datetime.now(),
                metrics={}
            )

    async def _monitor_resources(self):
        """Monitor system resource usage"""
        while self.active:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1) / 100
                self.resource_usage['cpu'].append(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.resource_usage['memory'].append(memory.percent / 100)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                self.resource_usage['disk'].append(disk.percent / 100)
                
                # Network usage
                network = psutil.net_io_counters()
                self.resource_usage['network'].append({
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv
                })
                
                # Keep last hour of data
                for key in self.resource_usage:
                    if len(self.resource_usage[key]) > 3600:
                        self.resource_usage[key] = self.resource_usage[key][-3600:]
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(5)

    async def _monitor_components(self):
        """Monitor component health"""
        while self.active:
            try:
                # Check each component
                for component in list(self.health_checks.keys()):
                    metrics = self.component_metrics.get(component, {})
                    
                    # Check error rate
                    error_rate = metrics.get('error_rate', 0)
                    latency = metrics.get('avg_latency', 0)
                    
                    # Update health status
                    self.health_checks[component] = (
                        error_rate < self.alert_thresholds['error_rate'] and
                        latency < self.alert_thresholds['latency']
                    )
                
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Component monitoring error: {e}")
                await asyncio.sleep(10)

    async def _monitor_performance(self):
        """Monitor system performance"""
        while self.active:
            try:
                # Calculate performance metrics
                for component, metrics in self.metrics_history.items():
                    if not metrics:
                        continue
                        
                    recent_metrics = metrics[-100:]  # Last 100 operations
                    
                    # Calculate averages
                    avg_latency = np.mean([m.get('latency', 0) for m in recent_metrics])
                    success_rate = np.mean([m.get('success', 0) for m in recent_metrics])
                    
                    self.component_metrics[component].update({
                        'avg_latency': avg_latency,
                        'success_rate': success_rate,
                        'error_rate': 1 - success_rate
                    })
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(5)

    async def _check_alerts(self):
        """Check for alert conditions"""
        while self.active:
            try:
                status = await self.check_health()
                
                if not status.healthy:
                    # Log alerts
                    for issue in status.issues:
                        self.logger.warning(f"System alert: {issue}")
                    
                    # Display alerts
                    await self._display_alerts(status)
                
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Alert check error: {e}")
                await asyncio.sleep(10)

    async def record_metric(self, 
                         component: str,
                         metric_type: str,
                         value: float):
        """Record performance metric"""
        try:
            metric = {
                'type': metric_type,
                'value': value,
                'timestamp': datetime.now().timestamp()
            }
            
            self.metrics_history[component].append(metric)
            
            # Keep last hour of metrics
            if len(self.metrics_history[component]) > 3600:
                self.metrics_history[component] = (
                    self.metrics_history[component][-3600:]
                )
                
        except Exception as e:
            self.logger.error(f"Error recording metric: {e}")

    async def record_error(self, 
                        component: str,
                        error: Exception):
        """Record component error"""
        self.error_counts[component] += 1
        await self.record_metric(
            component,
            'error',
            1.0
        )

    async def record_latency(self,
                          component: str,
                          latency: float):
        """Record operation latency"""
        self.latency_tracker[component].append(latency)
        await self.record_metric(
            component,
            'latency',
            latency
        )

    async def _display_alerts(self, status: HealthStatus):
        """Display system alerts"""
        table = Table(title="System Alerts", style="bold red")
        
        table.add_column("Component", justify="left")
        table.add_column("Status", justify="center")
        table.add_column("Issues", justify="left")
        
        # Add component status
        for component, healthy in status.components.items():
            table.add_row(
                component,
                "✓" if healthy else "✗",
                "\n".join(
                    issue for issue in status.issues
                    if component in issue
                )
            )
        
        self.console.print(table)

    async def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        try:
            # Component metrics
            metrics = {
                'components': self.component_metrics,
                'errors': dict(self.error_counts),
                'latency': {
                    component: np.mean(latencies)
                    for component, latencies in self.latency_tracker.items()
                    if latencies
                }
            }
            
            # Resource metrics
            metrics['resources'] = {
                key: np.mean(values[-10:]) if isinstance(values[0], (int, float))
                else values[-1]
                for key, values in self.resource_usage.items()
                if values
            }
            
            # System health
            status = await self.check_health()
            metrics['health'] = {
                'healthy': status.healthy,
                'issues': len(status.issues),
                'last_check': status.last_check.isoformat()
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting metrics: {e}")
            return {}

    async def cleanup(self):
        """Cleanup monitoring system"""
        try:
            self.active = False
            
            # Clear data
            self.metrics_history.clear()
            self.resource_usage.clear()
            self.component_metrics.clear()
            self.error_counts.clear()
            
            self.logger.info("System Monitor cleanup completed")
        except Exception as e:
            self.logger.error(f"Monitor cleanup error: {e}")
            raise
