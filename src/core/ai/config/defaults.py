"""Default Configurations

Default configuration values for the gateway system.
"""

from typing import Dict, Any
from ..gateway.models import RoutingStrategy, ProviderStatus

# Default provider configuration
DEFAULT_PROVIDER_CONFIG: Dict[str, Any] = {
    "timeout": 30.0,
    "retry_limit": 3,
    "status": ProviderStatus.ACTIVE,
    "health_check_interval": 30,
    "circuit_breaker": {
        "failure_threshold": 5,
        "reset_timeout": 300,  # 5 minutes
        "half_open_timeout": 60  # 1 minute
    }
}

# Default model configuration
DEFAULT_MODEL_CONFIG: Dict[str, Any] = {
    "context_window": 4096,
    "max_tokens": 4096,
    "temperature_range": (0.0, 1.0),
    "default_temperature": 0.7,
    "supports_streaming": True,
    "supports_function_calling": False,
    "supports_vision": False,
    "token_limit": 4096,
    "cost_per_token": 0.0,
    "response_format": ["text"]
}

# Default gateway configuration
DEFAULT_GATEWAY_CONFIG: Dict[str, Any] = {
    "routing_strategy": RoutingStrategy.ADAPTIVE,
    "health_check_interval": 30,
    "metrics_enabled": True,
    "debug_mode": False,
    "request_timeout": 60.0,
    "max_retries": 3,
    "backoff_factor": 1.5,
    "metrics_retention_days": 7,
    "max_parallel_requests": 100,
    "rate_limits": {
        "requests_per_minute": 1000,
        "tokens_per_minute": 100000
    }
}

# Default routing configuration
DEFAULT_ROUTING_CONFIG: Dict[str, Any] = {
    "strategy": RoutingStrategy.ADAPTIVE,
    "health_weight": 0.3,
    "load_weight": 0.3,
    "capability_weight": 0.4,
    "error_penalty": 0.1,
    "latency_threshold": 5.0,
    "max_error_rate": 0.1
}

# Default health monitoring configuration
DEFAULT_HEALTH_CONFIG: Dict[str, Any] = {
    "check_interval": 30,
    "failure_threshold": 3,
    "timeout": 5.0,
    "retry_interval": 60,
    "success_threshold": 2,
    "metrics_window": 300  # 5 minutes
}

# Default metrics configuration
DEFAULT_METRICS_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "collection_interval": 60,
    "retention_period": 604800,  # 7 days in seconds
    "batch_size": 100,
    "max_samples": 1000,
    "alert_thresholds": {
        "error_rate": 0.1,
        "latency": 5.0,
        "availability": 0.99
    }
}

# Provider-specific defaults
PROVIDER_SPECIFIC_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "ollama": {
        "endpoint": "http://localhost:11434",
        "timeout": 60.0,
        "models": {
            "codellama": {
                "capabilities": [
                    "code_generation",
                    "code_analysis"
                ],
                "context_window": 8192,
                "supports_function_calling": True
            },
            "llama2": {
                "capabilities": [
                    "text_generation",
                    "pattern_analysis"
                ],
                "context_window": 4096
            }
        }
    },
    "lm_studio": {
        "endpoint": "http://localhost:1234",
        "timeout": 30.0,
        "models": {
            "mixtral": {
                "capabilities": [
                    "code_generation",
                    "text_generation",
                    "pattern_analysis"
                ],
                "context_window": 8192,
                "supports_function_calling": True
            }
        }
    },
    "tgpt": {
        "endpoint": "http://localhost:4891",
        "timeout": 45.0,
        "models": {
            "gpt4": {
                "capabilities": [
                    "code_generation",
                    "code_analysis",
                    "pattern_detection",
                    "text_generation"
                ],
                "context_window": 8192,
                "supports_function_calling": True,
                "supports_vision": True
            }
        }
    }
}

# Environment-specific defaults
ENVIRONMENT_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "development": {
        "debug_mode": True,
        "metrics_enabled": True,
        "health_check_interval": 60,
        "request_timeout": 120.0,
        "rate_limits": {
            "requests_per_minute": 100,
            "tokens_per_minute": 10000
        }
    },
    "staging": {
        "debug_mode": False,
        "metrics_enabled": True,
        "health_check_interval": 30,
        "request_timeout": 60.0,
        "rate_limits": {
            "requests_per_minute": 500,
            "tokens_per_minute": 50000
        }
    },
    "production": {
        "debug_mode": False,
        "metrics_enabled": True,
        "health_check_interval": 15,
        "request_timeout": 30.0,
        "rate_limits": {
            "requests_per_minute": 1000,
            "tokens_per_minute": 100000
        }
    }
}

def get_environment_config(environment: str = "development") -> Dict[str, Any]:
    """Get environment-specific configuration"""
    return ENVIRONMENT_DEFAULTS.get(environment, ENVIRONMENT_DEFAULTS["development"])

def get_provider_defaults(provider: str) -> Dict[str, Any]:
    """Get provider-specific default configuration"""
    return PROVIDER_SPECIFIC_DEFAULTS.get(provider, DEFAULT_PROVIDER_CONFIG)
