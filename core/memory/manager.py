"""Memory Management System"""

import asyncio
from typing import Dict, Optional
import psutil
from dataclasses import dataclass
import logging

@dataclass
class MemoryPool:
    """Memory pool configuration"""
    total: int
    used: int = 0
    peak: int = 0
    allocations: Dict[str, int] = None

class MemoryManager:
    """Manages system memory allocation and optimization"""
    
    def __init__(self):
        self.pools = {
            'lm_studio': MemoryPool(total=24 * 1024 * 1024 * 1024),  # 24GB
            'ollama': MemoryPool(total=16 * 1024 * 1024 * 1024),     # 16GB
            'jan': MemoryPool(total=8 * 1024 * 1024 * 1024)          # 8GB
        }
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> bool:
        """Initialize memory management"""
        try:
            # Initialize pools
            for name, pool in self.pools.items():
                pool.allocations = {}
                self.logger.info(f"Initialized memory pool: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Memory initialization failed: {e}")
            return False

    async def allocate(self, requirements: Dict[str, int]) -> bool:
        """Allocate memory for task execution"""
        try:
            for pool_name, required in requirements.items():
                pool = self.pools[pool_name]
                if pool.used + required > pool.total:
                    # Try optimization before failing
                    if not await self._optimize_pool(pool):
                        return False
                
                pool.used += required
                pool.peak = max(pool.peak, pool.used)
                
            return True
        except Exception as e:
            self.logger.error(f"Memory allocation failed: {e}")
            return False

    async def release(self, allocations: Dict[str, int]):
        """Release allocated memory"""
        for pool_name, amount in allocations.items():
            pool = self.pools[pool_name]
            pool.used = max(0, pool.used - amount)

    async def _optimize_pool(self, pool: MemoryPool) -> bool:
        """Optimize memory pool usage"""
        try:
            # Implement memory optimization strategies
            # For now, just check if system has enough memory
            system_memory = psutil.virtual_memory()
            return system_memory.available >= (pool.total - pool.used)
        except Exception as e:
            self.logger.error(f"Memory optimization failed: {e}")
            return False

    async def get_metrics(self) -> Dict:
        """Get memory metrics"""
        return {
            name: {
                'total': pool.total,
                'used': pool.used,
                'peak': pool.peak,
                'available': pool.total - pool.used,
                'usage_percent': (pool.used / pool.total) * 100
            }
            for name, pool in self.pools.items()
        }

    async def cleanup(self):
        """Cleanup memory management"""
        for pool in self.pools.values():
            pool.used = 0
            pool.allocations = {}
