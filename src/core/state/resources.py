"""System Resource Monitoring

This module implements system-specific resource monitoring for:
- Memory usage
- CPU usage
- Disk usage
- Network statistics
"""

import psutil
import asyncio
from typing import Dict
import logging

logger = logging.getLogger("state.resources")

async def get_memory_usage() -> Dict[str, float]:
    """Get detailed memory usage statistics"""
    try:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "free": memory.free,
            "percent": memory.percent / 100.0,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_free": swap.free,
            "swap_percent": swap.percent / 100.0
        }
    except Exception as e:
        logger.error(f"Failed to get memory usage: {e}")
        return {}

async def get_cpu_usage() -> Dict[str, float]:
    """Get detailed CPU usage statistics"""
    try:
        # Get CPU times for all CPUs
        cpu_times = psutil.cpu_times_percent(interval=1)

        # Get per-CPU usage
        per_cpu = psutil.cpu_percent(interval=1, percpu=True)

        usage = {
            "system": cpu_times.system / 100.0,
            "user": cpu_times.user / 100.0,
            "idle": cpu_times.idle / 100.0,
            "total": psutil.cpu_percent(interval=1) / 100.0
        }

        # Add per-CPU metrics
        for i, cpu in enumerate(per_cpu):
            usage[f"cpu_{i}"] = cpu / 100.0

        return usage
    except Exception as e:
        logger.error(f"Failed to get CPU usage: {e}")
        return {}

async def get_disk_usage() -> Dict[str, float]:
    """Get detailed disk usage statistics"""
    try:
        usage = {}

        # Get all disk partitions
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                disk_usage = psutil.disk_usage(partition.mountpoint)
                usage[partition.mountpoint] = {
                    "total": disk_usage.total,
                    "used": disk_usage.used,
                    "free": disk_usage.free,
                    "percent": disk_usage.percent / 100.0
                }
            except Exception as e:
                logger.warning(f"Failed to get disk usage for {partition.mountpoint}: {e}")
                continue

        return usage
    except Exception as e:
        logger.error(f"Failed to get disk usage: {e}")
        return {}

async def get_network_stats() -> Dict[str, Dict]:
    """Get detailed network statistics"""
    try:
        # Get network interfaces
        interfaces = psutil.net_if_stats()
        counters = psutil.net_io_counters(pernic=True)

        stats = {}
        for interface, interface_stats in interfaces.items():
            if interface in counters:
                counter = counters[interface]
                stats[interface] = {
                    "bytes_sent": counter.bytes_sent,
                    "bytes_recv": counter.bytes_recv,
                    "packets_sent": counter.packets_sent,
                    "packets_recv": counter.packets_recv,
                    "errors_in": counter.errin,
                    "errors_out": counter.errout,
                    "speed": interface_stats.speed,
                    "mtu": interface_stats.mtu,
                    "is_up": interface_stats.isup
                }

        return stats
    except Exception as e:
        logger.error(f"Failed to get network stats: {e}")
        return {}

async def get_process_resources(pid: int) -> Dict[str, float]:
    """Get resource usage for a specific process"""
    try:
        process = psutil.Process(pid)

        with process.oneshot():
            memory_info = process.memory_info()
            cpu_times = process.cpu_times()

            return {
                "memory_rss": memory_info.rss,
                "memory_vms": memory_info.vms,
                "cpu_user": cpu_times.user,
                "cpu_system": cpu_times.system,
                "cpu_percent": process.cpu_percent() / 100.0,
                "threads": process.num_threads(),
                "fds": process.num_fds() if hasattr(process, 'num_fds') else None,
                "context_switches": process.num_ctx_switches().voluntary +
                                  process.num_ctx_switches().involuntary
            }
    except Exception as e:
        logger.error(f"Failed to get process resources for PID {pid}: {e}")
        return {}
