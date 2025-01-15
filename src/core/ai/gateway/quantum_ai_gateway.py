"""Core Gateway Module for Model Orchestration"""

# Standard library imports
import asyncio
import json
import hashlib
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import logging

# Third-party imports
import aiohttp
import websockets
import mitmproxy
from cryptography.fernet import Fernet
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GatewayError(Exception):
    """Base exception class for gateway errors."""
    pass

class ModelExecutionError(GatewayError):
    """Raised when model execution fails."""
    pass

class BackendConnectionError(GatewayError):
    """Raised when backend connection fails."""
    pass

@dataclass
class ModelState:
    """Tracks the state of model interactions"""
    active_models: Dict[str, float]  # Model -> coherence mapping
    state_vector: List[float]  # State amplitudes
    interaction_history: List[Dict]
    coherence_threshold: float = 0.7

@dataclass
class GatewayMetrics:
    """Tracks gateway performance metrics."""
    request_count: int = 0
    error_count: int = 0
    total_latency: float = 0.0
    model_latencies: Dict[str, List[float]] = None
    model_success_rates: Dict[str, float] = None
    last_update: datetime = None

    def __post_init__(self):
        self.model_latencies = {}
        self.model_success_rates = {}
        self.last_update = datetime.now()

class RequestInterceptor:
    """Handles request interception and processing."""

    def __init__(self):
        # Initialize any necessary state or configurations
        self.active = False

    async def start(self):
        """Prepare the interceptor for operation."""
        self.active = True
        print("Interceptor started.")

    async def intercept(self, request):
        """Intercept and process a request."""
        if not self.active:
            raise RuntimeError("Interceptor is not active.")
        # Implement interception logic here
        print(f"Intercepting request: {request}")
        return request  # Modify or log the request as needed

class ModelGateway:
    """Core orchestration layer for model interactions"""

    def __init__(self, config_path: Optional[Path] = None):
        # Load config from standard location
        config_path = config_path or Path(".config/ai/config.yml")
        if isinstance(config_path, dict):
            self.config = config_path
        else:
            config_path = Path(config_path) if isinstance(config_path, str) else config_path
            if not config_path.exists():
                raise FileNotFoundError(f"AI config not found at {config_path}")
            with open(config_path) as f:
                self.config = json.load(f)

        # Core component initialization
        self.model_state = ModelState(
            active_models={},
            state_vector=[],
            interaction_history=[]
        )

        # Define core backend interfaces from config
        self.backends = self.config.get("backends", {})
        if not self.backends:
            raise ValueError("No backend configurations found")

        # In the ModelGateway class
        self.interceptor = RequestInterceptor()

        # Initialize metrics
        self.metrics = GatewayMetrics()

        # Initialize monitoring
        self._setup_monitoring()

        # State management
        self._running = False
        self._cleanup_tasks = set()
        self._background_tasks = set()

    def _setup_monitoring(self):
        """Setup monitoring and metrics collection."""
        self.metrics = GatewayMetrics()
        logger.info("Monitoring system initialized")

    async def _update_metrics(self, model: str, latency: float, success: bool):
        """Update gateway metrics with new data."""
        self.metrics.request_count += 1
        self.metrics.total_latency += latency

        if not success:
            self.metrics.error_count += 1

        # Update model-specific metrics
        if model not in self.metrics.model_latencies:
            self.metrics.model_latencies[model] = []
        self.metrics.model_latencies[model].append(latency)

        # Calculate success rates
        total_requests = len(self.metrics.model_latencies[model])
        success_rate = 1.0 - (self.metrics.error_count / max(1, self.metrics.request_count))
        self.metrics.model_success_rates[model] = success_rate

        # Log metrics update
        logger.info(
            f"Metrics updated for model {model}",
            extra={
                "model": model,
                "latency": latency,
                "success_rate": success_rate,
                "total_requests": total_requests
            }
        )

    async def get_metrics(self) -> Dict:
        """Get current gateway metrics."""
        avg_latency = self.metrics.total_latency / max(1, self.metrics.request_count)

        return {
            "request_count": self.metrics.request_count,
            "error_count": self.metrics.error_count,
            "average_latency": avg_latency,
            "model_success_rates": self.metrics.model_success_rates,
            "uptime": (datetime.now() - self.metrics.last_update).total_seconds()
        }

    async def route_request(self, prompt: str, context: Dict = None) -> Dict:
        """Core routing interface"""
        state_vector = self._calculate_state_vector(prompt)
        model_probabilities = self._calculate_model_probabilities(state_vector)
        selected_models = await self._select_models(model_probabilities)

        results = await asyncio.gather(*[
            self._execute_model(model, prompt, context)
            for model in selected_models
        ])

        return await self._combine_results(results)

    async def _initialize_state(self):
        """Initialize the state of the ModelGateway."""
        # Initialize model state
        self.model_state = ModelState(
            active_models={model: 0.0 for model in self.backends.keys()},
            state_vector=[0.0] * len(self.backends),
            interaction_history=[]
        )

        # Log initialization
        print("ModelGateway state initialized.")

        # Prepare backend connections (if needed)
        # This is a placeholder for any connection setup logic
        for model, config in self.backends.items():
            print(f"Preparing connection for {model} at {config['host']}:{config['port']}")

        # Set up interceptors (if any)
        # This is a placeholder for interceptor setup
        self.interceptor = None  # Replace with actual interceptor setup
        print("Interceptors set up.")

    async def initialize(self):
        """Initialize the ModelGateway with proper setup."""
        try:
            # Initialize state
            await self._initialize_state()

            # Start interceptor
            self.interceptor = RequestInterceptor()
            await self.interceptor.start()

            # Initialize backend connections
            for model, config in self.backends.items():
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"http://{config['host']}:{config['port']}/health",
                            timeout=5.0
                        ) as response:
                            if response.status == 200:
                                self.model_state.active_models[model] = 1.0
                            else:
                                self.model_state.active_models[model] = 0.0
                except Exception as e:
                    print(f"Failed to initialize backend {model}: {e}")
                    self.model_state.active_models[model] = 0.0

            print("Gateway initialization complete.")
        except Exception as e:
            print(f"Failed to initialize gateway: {e}")
            raise

    async def _handle_error(self, error: Union[Exception, str], context: Dict = None) -> None:
        """Enhanced error handling with context and logging."""
        error_context = context or {}
        error_msg = str(error)

        if isinstance(error, ModelExecutionError):
            logger.error(f"Model execution failed: {error_msg}", extra=error_context)
        elif isinstance(error, BackendConnectionError):
            logger.error(f"Backend connection failed: {error_msg}", extra=error_context)
        else:
            logger.error(f"Unexpected error: {error_msg}", extra=error_context)

        # Record error in interaction history
        self.model_state.interaction_history.append({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "context": error_context
        })

        # Update model state if applicable
        if "model" in error_context:
            self.model_state.active_models[error_context["model"]] *= 0.8  # Reduce confidence

    # ... existing helper methods ...

    async def start(self):
        """Start the ModelGateway with proper lifecycle management."""
        if self._running:
            raise RuntimeError("Gateway is already running")

        try:
            self._running = True
            await self.initialize()

            # Start background monitoring task
            monitor_task = asyncio.create_task(self._monitor_health())
            self._background_tasks.add(monitor_task)

            logger.info("Gateway started successfully")

            while self._running:
                try:
                    request = await self._get_next_request()
                    if request:
                        response = await self.route_request(
                            request["prompt"],
                            request.get("context")
                        )
                        await self._send_response(response)
                    await self._update_state()
                except Exception as e:
                    await self._handle_error(e)
                    continue

        except asyncio.CancelledError:
            logger.info("Gateway shutdown initiated")
        except Exception as e:
            logger.error(f"Fatal error in gateway: {e}")
            raise
        finally:
            await self.cleanup()

    async def stop(self):
        """Stop the gateway gracefully."""
        logger.info("Stopping gateway...")
        self._running = False
        await self.cleanup()

    async def _monitor_health(self):
        """Monitor gateway health in background."""
        while self._running:
            try:
                # Check backend health
                for model, config in self.backends.items():
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                f"http://{config['host']}:{config['port']}/health",
                                timeout=5.0
                            ) as response:
                                is_healthy = response.status == 200
                                self.model_state.active_models[model] = 1.0 if is_healthy else 0.0
                    except Exception as e:
                        logger.warning(f"Health check failed for {model}: {e}")
                        self.model_state.active_models[model] = 0.0

                # Update metrics
                metrics = await self.get_metrics()
                logger.info("Health metrics updated", extra=metrics)

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(5)  # Back off on error

        logger.info("Health monitoring stopped")

    async def cleanup(self):
        """Cleanup gateway resources."""
        logger.info("Starting gateway cleanup...")

        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()

        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Close all active sessions
        for task in self._cleanup_tasks:
            try:
                await task
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

        self._running = False
        logger.info("Gateway cleanup completed")

    async def _get_next_request(self) -> Optional[Dict]:
        """Simulate getting the next request. Replace with actual logic."""
        # Placeholder for request retrieval logic
        await asyncio.sleep(1)  # Simulate waiting for a request
        return {"prompt": "Example prompt", "context": {}}

    async def _send_response(self, response: Dict):
        """Simulate sending a response. Replace with actual logic."""
        # Placeholder for response sending logic
        print(f"Response sent: {response}")

    def _calculate_state_vector(self, prompt: str) -> List[float]:
        """Calculate the state vector based on the given prompt."""
        # Placeholder logic for state vector calculation
        # This should be replaced with actual logic
        return [0.5] * len(self.backends)

    def _calculate_model_probabilities(self, state_vector: List[float]) -> Dict[str, float]:
        """Calculate model probabilities based on the state vector."""
        # Placeholder logic for calculating model probabilities
        # This should be replaced with actual logic
        total = sum(state_vector)
        return {model: (state / total) for model, state in zip(self.backends.keys(), state_vector)}

    async def _select_models(self, model_probabilities: Dict[str, float]) -> List[str]:
        """Select models based on calculated probabilities."""
        # Placeholder logic for selecting models
        # This should be replaced with actual logic
        sorted_models = sorted(model_probabilities.items(), key=lambda x: x[1], reverse=True)
        return [model for model, _ in sorted_models[:2]]  # Select top 2 models as an example

    async def _execute_model(self, model: str, prompt: str, context: Dict = None) -> Dict:
        """Execute request on specific model with monitoring and metrics."""
        start_time = datetime.now()
        error_context = {"model": model, "prompt_length": len(prompt)}

        try:
            config = self.backends[model]
            url = f"http://{config['host']}:{config['port']}/v1/completions"

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        url,
                        json={"prompt": prompt, "context": context},
                        timeout=30.0
                    ) as response:
                        if response.status != 200:
                            raise ModelExecutionError(
                                f"Model {model} failed with status {response.status}"
                            )

                        result = await response.json()
                        execution_time = (datetime.now() - start_time).total_seconds()

                        # Update metrics
                        await self._update_metrics(model, execution_time, True)

                        logger.info(
                            f"Successfully executed model {model}",
                            extra={
                                "model": model,
                                "status": response.status,
                                "execution_time": execution_time
                            }
                        )
                        return result

                except asyncio.TimeoutError:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    await self._update_metrics(model, execution_time, False)
                    raise BackendConnectionError(f"Timeout while connecting to model {model}")

                except aiohttp.ClientError as e:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    await self._update_metrics(model, execution_time, False)
                    raise BackendConnectionError(f"Connection error for model {model}: {str(e)}")

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._update_metrics(model, execution_time, False)
            await self._handle_error(e, error_context)
            return {"error": str(e), "model": model, "context": error_context}

    async def _combine_results(self, results: List[Dict]) -> Dict:
        """Combine results from multiple models."""
        valid_results = [r for r in results if "error" not in r]
        if not valid_results:
            return {"error": "All models failed to produce valid results"}

        # Combine responses based on model probabilities
        combined_response = {
            "results": valid_results,
            "timestamp": datetime.now().isoformat(),
            "model_count": len(valid_results)
        }
        return combined_response

    async def _update_state(self):
        """Update the gateway state based on recent interactions."""
        try:
            # Update model coherence values
            for model in self.model_state.active_models:
                recent_interactions = [
                    h for h in self.model_state.interaction_history[-10:]
                    if h.get("model") == model
                ]
                success_rate = sum(1 for h in recent_interactions if not h.get("error", False)) / max(1, len(recent_interactions))
                self.model_state.active_models[model] = min(1.0, success_rate + 0.1)

            # Prune history if too long
            if len(self.model_state.interaction_history) > 1000:
                self.model_state.interaction_history = self.model_state.interaction_history[-1000:]

        except Exception as e:
            await self._handle_error(e)

# Configuration
config = {
    "threshold": 0.7,
    "coherence_factor": 0.85,
    "uncertainty_scale": 0.15,
    "backends": {
        "model1": {"host": "localhost", "port": 8000},
        "model2": {"host": "localhost", "port": 8001}
    }
}

gateway = ModelGateway(config)
asyncio.run(gateway.start())
