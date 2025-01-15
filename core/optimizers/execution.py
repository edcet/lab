import psutil
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class CacheEntry:
    data: Any
    timestamp: datetime
    ttl: timedelta = field(default=timedelta(hours=1))

    def is_valid(self) -> bool:
        return datetime.now() - self.timestamp < self.ttl

class ExecutionOptimizer:
    def __init__(self, max_memory_percent: float = 90.0, cache_ttl: timedelta = timedelta(hours=1)):
        self.max_memory_percent = max_memory_percent
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.logger = logging.getLogger(__name__)

    def check_resources(self) -> bool:
        """Check if system has enough resources for execution."""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            
            if memory.percent >= self.max_memory_percent:
                self.logger.warning(f"Memory usage too high: {memory.percent}%")
                return False
            
            if cpu_percent >= 90:
                self.logger.warning(f"CPU usage too high: {cpu_percent}%")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error checking resources: {str(e)}")
            return False

    def optimize_path(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize execution path based on model configuration and system resources."""
        try:
            optimized_config = model_config.copy()
            
            if not self.check_resources():
                # Adjust batch size or precision based on resource availability
                optimized_config["batch_size"] = max(1, optimized_config.get("batch_size", 1) // 2)
                optimized_config["precision"] = "float16"
            
            return optimized_config
        except Exception as e:
            self.logger.error(f"Error optimizing execution path: {str(e)}")
            return model_config

    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieve result from cache if available and valid."""
        try:
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                if entry.is_valid():
                    return entry.data
                else:
                    del self.cache[cache_key]
            return None
        except Exception as e:
            self.logger.error(f"Error accessing cache: {str(e)}")
            return None

    def store_in_cache(self, cache_key: str, data: Any) -> bool:
        """Store result in cache with timestamp."""
        try:
            self.cache[cache_key] = CacheEntry(
                data=data,
                timestamp=datetime.now(),
                ttl=self.cache_ttl
            )
            return True
        except Exception as e:
            self.logger.error(f"Error storing in cache: {str(e)}")
            return False

    def cleanup_cache(self) -> None:
        """Remove expired entries from cache."""
        try:
            current_time = datetime.now()
            expired_keys = [
                key for key, entry in self.cache.items()
                if current_time - entry.timestamp >= entry.ttl
            ]
            for key in expired_keys:
                del self.cache[key]
        except Exception as e:
            self.logger.error(f"Error cleaning up cache: {str(e)}")

