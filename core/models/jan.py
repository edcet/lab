"""Jan API Client with advanced streaming, caching and error recovery"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, AsyncGenerator, Union

import aiohttp
import asyncio
import backoff
from aiohttp import ClientTimeout, TCPConnector
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, Info
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

class JanClient:
    """
    Async client for Jan's AI API with advanced features:
    - Robust connection pooling and backoff/retry
    - Prometheus metrics integration 
    - Advanced error handling and recovery
    - Request/response caching
    - Health monitoring and circuit breaking
    """

    def __init__(self, base_url: str = "http://localhost:1337"):
        # Base configuration
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self.models: Dict[str, Any] = {}

        # Cache configuration with TTL
        self.cache: Dict[str, Any] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_ttl = 300  # 5 minutes
        # Create custom Prometheus registry and client info
        self.metrics_registry = prometheus_client.CollectorRegistry()
        self.client_info = Info('jan_client_info', 'Jan client configuration information',
                            registry=self.metrics_registry)
        self.client_info.info({
            'base_url': self.base_url,
            'pool_size': str(self.pool_size),
            'version': '1.0.0'
        })

        # Request metrics
        self.request_counter = Counter(
            'jan_api_requests_total',
            'Total number of API requests made',
            ['endpoint', 'method', 'status'],
            registry=self.metrics_registry
        )

        # Latency metrics with buckets optimized for API calls
        self.latency_histogram = Histogram(
            'jan_api_latency_seconds',
            'API call latency distribution',
            ['endpoint', 'operation'],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
            registry=self.metrics_registry
        )

        # Error tracking
        self.error_counter = Counter(
            'jan_api_errors_total',
            'Total number of API errors encountered',
            ['endpoint', 'error_type', 'error_code'],
            registry=self.metrics_registry
        )

        # Resource utilization
        self.active_requests_gauge = Gauge(
            'jan_api_active_requests',
            'Number of currently active API requests',
            ['endpoint'],
            registry=self.metrics_registry
        )

        # Circuit breaker status
        self.circuit_breaker_gauge = Gauge(
            'jan_api_circuit_breaker_status',
            'Circuit breaker status (0=closed, 1=open)',
            ['endpoint'],
            registry=self.metrics_registry
        )

        # Cache metrics
        self.cache_info_gauge = Gauge(
            'jan_api_cache_info',
            'Cache statistics',
            ['metric'],
            registry=self.metrics_registry
        )

        # Performance metrics
        self.metrics = {
            'requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_duration': 0.0,
            'average_latency': 0.0,
            'circuit_breaks': 0,
            'active_connections': 0
        }

        # Health tracking
        self.last_health_check: Optional[datetime] = None
        self.is_healthy = False

        # Connection pool config
        self.pool_size = 10
        self.pool_timeout = 30
        self.max_retries = 3
        self.circuit_timeout = 60

        # Resource tracking
        self.active_requests = 0
        self.peak_memory = 0

        # Circuit breaker state
        self.circuit_open = False
        self.failures = 0
        self.last_failure: Optional[float] = None
        
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3
    )
    async def initialize(self) -> bool:
        """Initialize client with connection pool and verify connection"""
        try:
            # Configure connection pooling
            connector = TCPConnector(
                limit=self.pool_size,
                keepalive_timeout=self.pool_timeout,
                force_close=False,
                enable_cleanup_closed=True
            )
            
            # Set timeouts
            timeout = ClientTimeout(
                total=30,
                connect=10,
                sock_read=10
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
            self.logger.info("Initializing Jan client")
            
            # Verify connection
            if not await self._verify_connection():
                raise ConnectionError("Failed to connect to Jan API")
            
            # Load model configurations
            if not await self._load_models():
                raise RuntimeError("Failed to load Jan model configurations")
            
            self.is_healthy = True
            self.last_health_check = datetime.now()
            self.circuit_breaker_gauge.set(0)
            self.logger.info("Jan client initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Jan client initialization failed: {e}")
            self.error_counter.labels(type='initialization').inc()
            return False
        
    async def _verify_connection(self) -> bool:
        """Verify API connection and health"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200  
        except Exception as e:
            self.logger.error(f"Jan API connection check failed: {e}")
            return False
            
    async def _load_models(self) -> bool:
        """Load available model configurations"""  
        try:
            async with self.session.get(f"{self.base_url}/models") as response:
                if response.status == 200:
                    self.models = await response.json()
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to load Jan models: {e}")
            return False

    async def _check_circuit_breaker(self) -> None:
        """Check circuit breaker status and handle state transitions"""
        if self.circuit_open:
            if time.time() - (self.last_failure or 0) > self.circuit_timeout:
                self.circuit_open = False
                self.failures = 0
                self.circuit_breaker_gauge.set(0)
                self.logger.info("Circuit breaker closed")
            else:
                raise Exception("Circuit breaker is open")

    async def _update_metrics(self, success: bool, duration: float, endpoint: str) -> None:
        """Update performance metrics and Prometheus gauges"""
        if success:
            self.metrics['successful_requests'] += 1
        else:
            self.metrics['failed_requests'] += 1
            
        self.metrics['total_duration'] += duration
        self.metrics['average_latency'] = (
            self.metrics['total_duration'] / 
            self.metrics['requests']
        )
        
        self.metrics['active_connections'] = self.active_requests
        self.active_requests_gauge.set(self.active_requests)
        self.latency_histogram.labels(endpoint=endpoint).observe(duration)

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3
    )
    async def generate_stream(self,
                prompt: str,
                model: str = "janai-large", 
                max_tokens: int = 1000,
                temperature: float = 0.7,
                cache_key: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream generate text with caching, metrics and error handling"""
        
        # Check circuit breaker
        if self.circuit_open:
            if time.time() - self.last_failure > self.circuit_timeout:
                self.circuit_open = False
                self.failures = 0
            else:
                raise Exception("Circuit breaker is open")
                
        try:
            start_time = time.time()
            self.active_requests += 1
            self.metrics['requests'] += 1
            
            # Prepare request
            payload = {
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True
            }
            
            async with self.session.post(
                f"{self.base_url}/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    raise Exception(f"Jan API error: {response.status}")
                    
                async for chunk in response.content:
                    if chunk:
                        yield chunk.decode('utf-8')
                        
            duration = time.time() - start_time
            await self._update_metrics(True, duration)
            
        except Exception as e:
            self.logger.error(f"Jan streaming failed: {e}")
            duration = time.time() - start_time
            await self._update_metrics(False, duration)
            await self._handle_failure()
            raise
            
        finally:
            self.active_requests -= 1

    async def generate(self, 
                    prompt: str,
                    model: str = "janai-large",
                    max_tokens: int = 1000,
                    temperature: float = 0.7,
                    cache_key: Optional[str] = None) -> Dict[str, Any]:
        """Generate text using Jan's API with caching and metrics"""
        start_time = time.time()
        
        try:
            # Check circuit breaker
            if self.circuit_open:
                if time.time() - self.last_failure > self.circuit_timeout:
                    self.circuit_open = False 
                    self.failures = 0
                else:
                    raise Exception("Circuit breaker is open")
        
            # Check cache
            if cache_key and cache_key in self.cache:
                self.cache_hits += 1
                return self.cache[cache_key]
            self.cache_misses += 1
            
            # Track request
            self.active_requests += 1
            self.metrics['requests'] += 1
            
            # Prepare request
            payload = {
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens, 
                "temperature": temperature
            }
            
            # Make request
            async with self.session.post(
                f"{self.base_url}/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    raise Exception(f"Jan API error: {response.status}")
                    
                result = await response.json()
                
                # Update cache
                if cache_key:
                    self.cache[cache_key] = result
                    
                # Update metrics
                duration = time.time() - start_time
                await self._update_metrics(True, duration)
                
                return result
                
        except Exception as e:
            self.logger.error(f"Jan generation failed: {e}")
            duration = time.time() - start_time
            await self._update_metrics(False, duration)
            await self._handle_failure()
            raise
            
        finally:
            self.active_requests -= 1

    async def batch_generate(self,
                        prompts: List[Dict],
                        batch_size: int = 10) -> List[Dict]:
        """Process multiple prompts in batches"""
        results = []
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.generate(**prompt) for prompt in batch]
            )
            results.extend(batch_results)
        return results
            
    async def _handle_failure(self):
        """Handle failures and circuit breaking"""
        self.failures += 1
        self.last_failure = time.time()
        self.metrics['circuit_breaks'] += 1
        
        if self.failures >= self.max_retries:
            self.circuit_open = True
            self.logger.warning("Circuit breaker opened")
            
    async def _update_metrics(self, success: bool, duration: float):
        """Update performance metrics"""
        if success:
            self.metrics['successful_requests'] += 1
        else:
            self.metrics['failed_requests'] += 1
            
        self.metrics['total_duration'] += duration
        self.metrics['average_latency'] = (
            self.metrics['total_duration'] / 
            self.metrics['requests']
        )
        self.metrics['active_connections'] = self.active_requests
        
    async def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        if self.metrics['requests'] == 0:
            return {
                **self.metrics,
                'success_rate': 1.0,
                'cache_hit_rate': 0.0,
                'health_status': self.is_healthy
            }
            
        return {
            **self.metrics,
            'success_rate': (
                self.metrics['successful_requests'] /
                self.metrics['requests']
            ),
            'cache_hit_rate': (
                self.cache_hits / 
                (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0
                else 0.0
            ),
            'health_status': self.is_healthy,
            'circuit_breaker_status': 'open' if self.circuit_open else 'closed'
        }
        
    async def cleanup(self) -> None:
        """Cleanup resources and reset client state"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
                
            self.cache.clear()
            self.models.clear()
            self.is_healthy = False
            self.circuit_open = False
            self.failures = 0
            self.last_failure = None
            
            # Reset metrics
            self.active_requests_gauge.set(0)
            self.circuit_breaker_gauge.set(0)
            self.metrics = {k: 0 for k in self.metrics}
            
            self.logger.info("Jan client cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            self.error_counter.labels(type='cleanup').inc()
            raise

@backoff.on_exception(
    backoff.expo,
    (aiohttp.ClientError, asyncio.TimeoutError),
    max_tries=3
)
async def health_check(self) -> bool:
    """Check API health and update status"""
    try:
        start_time = time.time()
        async with self.session.get(f"{self.base_url}/health") as response:
            healthy = response.status == 200
            duration = time.time() - start_time
            await self._update_metrics(healthy, duration, "health_check")
            self.is_healthy = healthy
            self.last_health_check = datetime.now()
            return healthy
    except Exception as e:
        self.logger.error(f"Health check failed: {e}")
        self.is_healthy = False
        return False
    
    def __init__(self, base_url: str = "http://localhost:1337"):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.models = {}
        
        # Cache configuration
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Performance metrics  
        self.metrics = {
            'requests': 0, 
            'successful_requests': 0,
            'failed_requests': 0,
            'total_duration': 0.0,
            'average_latency': 0.0
        }
        
        # Health tracking
        self.last_health_check = None
        self.is_healthy = False
        
        # Resource tracking
        self.active_requests = 0
        self.peak_memory = 0
        
    async def initialize(self) -> bool:
        """Initialize the client and verify connection"""
        try:
            self.session = aiohttp.ClientSession()
            self.logger.info("Initializing Jan client")
            
            # Verify connection
            if not await self._verify_connection():
                raise ConnectionError("Failed to connect to Jan API")
            
            # Load model configurations
            if not await self._load_models():
                raise RuntimeError("Failed to load Jan model configurations")
            
            self.is_healthy = True
            self.last_health_check = datetime.now()
            self.logger.info("Jan client initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Jan client initialization failed: {e}")
            return False
        
    async def _verify_connection(self) -> bool:
        """Verify API connection and health"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception as e:
            self.logger.error(f"Jan API connection check failed: {e}")
            return False
            
    async def _load_models(self) -> bool:
        """Load available model configurations"""
        try:
            async with self.session.get(f"{self.base_url}/models") as response:
                if response.status == 200:
                    self.models = await response.json()
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to load Jan models: {e}")
            return False
        
    async def generate(self, 
                prompt: str,
                model: str = "janai-large",
                max_tokens: int = 1000,
                temperature: float = 0.7,
                cache_key: Optional[str] = None) -> Dict[str, Any]:
        """Generate text using Jan's API with caching and metrics"""
        start_time = time.time()
        
        try:
            # Check cache
            if cache_key and cache_key in self.cache:
                self.cache_hits += 1
                return self.cache[cache_key]
            self.cache_misses += 1
            
            # Track request
            self.active_requests += 1
            self.metrics['requests'] += 1
            
            # Prepare request
            payload = {
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Make request
            async with self.session.post(
                f"{self.base_url}/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    raise Exception(f"Jan API error: {response.status}")
                    
                result = await response.json()
                
                # Update cache
                if cache_key:
                    self.cache[cache_key] = result
                    
                # Update metrics
                duration = time.time() - start_time
                await self._update_metrics(True, duration)
                
                return result
                
        except Exception as e:
            self.logger.error(f"Jan generation failed: {e}")
            duration = time.time() - start_time
            await self._update_metrics(False, duration)
            raise
            
        finally:
            self.active_requests -= 1
            
    async def _update_metrics(self, success: bool, duration: float):
        """Update performance metrics"""
        if success:
            self.metrics['successful_requests'] += 1
        else:
            self.metrics['failed_requests'] += 1
            
        self.metrics['total_duration'] += duration
        self.metrics['average_latency'] = (
            self.metrics['total_duration'] / 
            self.metrics['requests']
        )
        
    async def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        if self.metrics['requests'] == 0:
            return {
                **self.metrics,
                'success_rate': 1.0,
                'cache_hit_rate': 0.0,
                'health_status': self.is_healthy
            }
            
        return {
            **self.metrics,
            'success_rate': (
                self.metrics['successful_requests'] /
                self.metrics['requests']
            ),
            'cache_hit_rate': (
                self.cache_hits / 
                (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0
                else 0.0
            ),
            'health_status': self.is_healthy
        }
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None
            
        self.cache.clear()
        self.models.clear()
        self.is_healthy = False

"""Jan API Client with advanced streaming, caching and error recovery"""

@backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3)
async def batch_generate(self, prompts: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
    """Process a batch of prompts in parallel with retry and error handling"""
    results = []
    try:
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.generate(**prompt) for prompt in batch],
                return_exceptions=True
            )
            
            # Filter out exceptions and log errors
            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Batch generation error: {result}")
                    self.error_counter.labels(type='batch_generation').inc()
                    results.append({"error": str(result)})
                else:
                    results.append(result)
                    
        return results
    except Exception as e:
        self.logger.error(f"Batch processing failed: {e}")
        raise
    
    def __init__(self, base_url: str = "http://localhost:1337"):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.models = {}
        
        # Cache configuration
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Performance metrics
        self.metrics = {
            'requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_duration': 0.0,
            'average_latency': 0.0
        }
        
        # Health tracking
        self.last_health_check = None
        self.is_healthy = False
        
        # Resource tracking
        self.active_requests = 0
        self.peak_memory = 0
        
    async def initialize(self) -> bool:
        """Initialize the client and verify connection"""
        try:
            self.session = aiohttp.ClientSession()
            self.logger.info("Initializing Jan client")
            
            # Verify connection
            if not await self._verify_connection():
                raise ConnectionError("Failed to connect to Jan API")
            
            # Load model configurations
            if not await self._load_models():
                raise RuntimeError("Failed to load Jan model configurations")
            
            self.is_healthy = True
            self.last_health_check = datetime.now()
            self.logger.info("Jan client initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Jan client initialization failed: {e}")
            return False
        
    async def _verify_connection(self) -> bool:
        """Verify API connection and health"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception as e:
            self.logger.error(f"Jan API connection check failed: {e}")
            return False
            
    async def _load_models(self) -> bool:
        """Load available model configurations"""
        try:
            async with self.session.get(f"{self.base_url}/models") as response:
                if response.status == 200:
                    self.models = await response.json()
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to load Jan models: {e}")
            return False
        
    async def generate(self, 
                    prompt: str,
                    model: str = "janai-large",
                    max_tokens: int = 1000,
                    temperature: float = 0.7,
                    cache_key: Optional[str] = None) -> Dict[str, Any]:
        """Generate text using Jan's API with caching and metrics"""
        start_time = time.time()
        
        try:
            # Check cache
            if cache_key and cache_key in self.cache:
                self.cache_hits += 1
                return self.cache[cache_key]
            self.cache_misses += 1
            
            # Track request
            self.active_requests += 1
            self.metrics['requests'] += 1
            
            # Prepare request
            payload = {
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Make request
            async with self.session.post(
                f"{self.base_url}/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    raise Exception(f"Jan API error: {response.status}")
                    
                result = await response.json()
                
                # Update cache
                if cache_key:
                    self.cache[cache_key] = result
                    
                # Update metrics
                duration = time.time() - start_time
                await self._update_metrics(True, duration)
                
                return result
                
        except Exception as e:
            self.logger.error(f"Jan generation failed: {e}")
            duration = time.time() - start_time
            await self._update_metrics(False, duration)
            raise
            
        finally:
            self.active_requests -= 1
            
    async def _update_metrics(self, success: bool, duration: float):
        """Update performance metrics"""
        if success:
            self.metrics['successful_requests'] += 1
        else:
            self.metrics['failed_requests'] += 1
            
        self.metrics['total_duration'] += duration
        self.metrics['average_latency'] = (
            self.metrics['total_duration'] / 
            self.metrics['requests']
        )
        
    async def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        if self.metrics['requests'] == 0:
            return {
                **self.metrics,
                'success_rate': 1.0,
                'cache_hit_rate': 0.0,
                'health_status': self.is_healthy
            }
            
        return {
            **self.metrics,
            'success_rate': (
                self.metrics['successful_requests'] /
                self.metrics['requests']
            ),
            'cache_hit_rate': (
                self.cache_hits / 
                (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0
                else 0.0
            ),
            'health_status': self.is_healthy
        }
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None
            
        self.cache.clear()
        self.models.clear()
        self.is_healthy = False

