from typing import Dict, Any

DEFAULT_CONFIG: Dict[str, Any] = {
    # Memory Configuration
    "memory": {
        "store_patterns": True,
        "learn_from_history": True,
        "optimize_retrieval": True,
        "max_memory_items": 10000,
        "pattern_recognition_threshold": 0.75
    },

    # Evolution Configuration
    "evolution": {
        "performance_threshold": 0.85,
        "efficiency_minimum": 0.75,
        "cost_optimization": True,
        "evolution_rate": "progressive",
        "capability_enhancement_threshold": 0.8
    },

    # Performance Metrics
    "performance": {
        "track_metrics": True,
        "metrics_history_size": 1000,
        "efficiency_weight": 0.4,
        "cost_weight": 0.3,
        "success_weight": 0.3
    },

    # Error Handling
    "error_handling": {
        "autonomous_recovery": True,
        "learn_from_failures": True,
        "adaptive_responses": True,
        "max_retry_attempts": 3,
        "error_threshold": 0.1
    },

    # Thought Process
    "thought_process": {
        "deep_analysis": True,
        "pattern_recognition": True,
        "self_criticism": True,
        "continuous_refinement": True,
        "reasoning_depth": 3
    },

    # Action Selection
    "action_selection": {
        "optimization_strategy": "balanced",  # Options: aggressive, balanced, conservative
        "cost_threshold": 0.5,
        "efficiency_target": 0.9,
        "exploration_rate": 0.1
    },

    # System Resources
    "system": {
        "memory_capacity": "adaptive",  # Options: fixed, adaptive
        "processing_priority": "balanced",  # Options: speed, accuracy, balanced
        "resource_allocation": "dynamic"  # Options: static, dynamic
    }
}

def load_config(custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Load configuration with custom overrides

    Args:
        custom_config: Dictionary containing custom configuration values

    Returns:
        Complete configuration dictionary with custom overrides applied
    """
    config = DEFAULT_CONFIG.copy()

    if custom_config:
        for category, settings in custom_config.items():
            if category in config:
                if isinstance(settings, dict):
                    config[category].update(settings)
                else:
                    config[category] = settings

    return config

def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate configuration values

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if configuration is valid, raises ValueError otherwise
    """
    required_categories = [
        "memory", "evolution", "performance",
        "error_handling", "thought_process",
        "action_selection", "system"
    ]

    # Check for required categories
    for category in required_categories:
        if category not in config:
            raise ValueError(f"Missing required configuration category: {category}")

    # Validate specific values
    if config["evolution"]["performance_threshold"] < 0 or config["evolution"]["performance_threshold"] > 1:
        raise ValueError("Performance threshold must be between 0 and 1")

    if config["evolution"]["efficiency_minimum"] < 0 or config["evolution"]["efficiency_minimum"] > 1:
        raise ValueError("Efficiency minimum must be between 0 and 1")

    if config["action_selection"]["optimization_strategy"] not in ["aggressive", "balanced", "conservative"]:
        raise ValueError("Invalid optimization strategy")

    if config["system"]["memory_capacity"] not in ["fixed", "adaptive"]:
        raise ValueError("Invalid memory capacity setting")

    if config["system"]["processing_priority"] not in ["speed", "accuracy", "balanced"]:
        raise ValueError("Invalid processing priority setting")

    if config["system"]["resource_allocation"] not in ["static", "dynamic"]:
        raise ValueError("Invalid resource allocation setting")

    return True
