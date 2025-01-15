"""LM Studio Integration with optimized request handling"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from cachetools import TTLCache

class LMStudioClient:
    """Optimized LM Studio API client"""
    
    def __init__(self, endpoint: str = "http://localhost:1234"):
        self.endpoint = endpoint
        self.session: Optional[aiohttp.ClientSession] = None
        self.response_cache = TTLCache(maxsize=1000, ttl=3600)
        self.model_configs = {}
        self.request_semaphore = asyncio.Semaphore(4)  # Max concurrent requests
        self.logger = logging.getLogger(__name__)
        self.metrics = {
            'requests': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_latency': 0
        }

    async def initialize(self) -> bool:
        """Initialize client and verify connection"""
        try:
            self.session = aiohttp.ClientSession()
            await self._verify_connection()
            await self._load_model_configs()
            return True
        except Exception as e:
            self.logger.error(f"LM Studio initialization failed: {e}")
            return False

    async def _verify_connection(self) -> bool:
        """Verify API connection"""
        try:
            async with self.session.get(f"{self.endpoint}/v1/models") as response:
                if response.status == 200:
                    return True
                raise ConnectionError(f"API returned status {response.status}")
        except Exception as e:
            self.logger.error(f"Connection verification failed: {e}")
            raise

    async def _load_model_configs(self):
        """Load and cache model configurations"""
        try:
            async with self.session.get(f"{self.endpoint}/v1/models") as response:
                models = await response.json()
                for model in models['data']:
                    self.model_configs[model['id']] = {
                        'id': model['id'],
                        'max_tokens': 4096,  # Default
                        'batch_enabled': True
                    }
        except Exception as e:
            self.logger.error(f"Failed to load model configs: {e}")
            raise

    async def generate(self, 
                    prompt: str, 
                    model: str = "codestral-22b-v0.1", 
                    **kwargs) -> Dict[str, Any]:
        """Generate completion with optimized handling"""
        cache_key = self._get_cache_key(prompt, model, kwargs)
        
        # Check cache
        if cached := self.response_cache.get(cache_key):
            self.metrics['cache_hits'] += 1
            return cached

        start_time = datetime.now()
        try:
            async with self.request_semaphore:
                payload = self._prepare_payload(prompt, model, **kwargs)
                async with self.session.post(
                    f"{self.endpoint}/v1/chat/completions",
                    json=payload
                ) as response:
                    if response.status != 200:
                        raise Exception(f"API error: {response.status}")
                    
                    result = await response.json()
                    
                    # Update metrics
                    self.metrics['requests'] += 1
                    self.metrics['total_latency'] += (
                        datetime.now() - start_time
                    ).total_seconds()
                    
                    # Cache result
                    self.response_cache[cache_key] = result
                    return result

        except Exception as e:
            self.metrics['errors'] += 1
            self.logger.error(f"Generation failed: {e}")
            raise

    def _get_cache_key(self, prompt: str, model: str, kwargs: Dict) -> str:
        """Generate cache key for request"""
        key_parts = [
            prompt,
            model,
            str(sorted(kwargs.items()))
        ]
        return "|".join(key_parts)

    def _prepare_payload(self, 
                      prompt: str, 
                      model: str, 
                      **kwargs) -> Dict[str, Any]:
        """Prepare optimized API payload"""
        return {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get('temperature', 0.1),
            "max_tokens": kwargs.get('max_tokens', 
                                   self.model_configs[model]['max_tokens']),
            "stream": False  # Streaming not needed for system tasks
        }

    async def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        avg_latency = (
            self.metrics['total_latency'] / 
            max(1, self.metrics['requests'])
        )
        
        return {
            **self.metrics,
            'average_latency': avg_latency,
            'cache_hit_ratio': (
                self.metrics['cache_hits'] / 
                max(1, self.metrics['requests'])
            ),
            'error_rate': (
                self.metrics['errors'] / 
                max(1, self.metrics['requests'])
            )
        }

    async def cleanup(self):
        """Cleanup client resources"""
        if self.session:
            await self.session.close()
        self.response_cache.clear()
