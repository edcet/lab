"""Integration tests for the unified system"""

import asyncio
import pytest
import pytest_asyncio
from pathlib import Path
import logging
import json
import yaml

from core.unified_system import UnifiedSystem
from core.orchestrator import Orchestrator
from core.radical_store import RadicalStore
from core.health_monitor import HealthMonitor
from core.quantum_ai_gateway import ModelGateway
from core.credentials import CredentialManager
from core.platform import PlatformManager
from core.safety_intermediary import SafetyIntermediary
from core.neural_manipulator import NeuralManipulator
from core.ai_gateway_controller import AIGatewayController
from core.local_ai_orchestrator import LocalAIOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest_asyncio.fixture(scope="session")
async def event_loop():
    """Create an instance of the default event loop for the entire test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    tasks = asyncio.all_tasks(loop)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await loop.shutdown_asyncgens()
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def unified_system(event_loop):
    """Create a UnifiedSystem instance for testing."""
    config_path = Path(".test_workspace/.config/system/config.json")
    workspace_root = Path(".test_workspace")
    system = UnifiedSystem(config_path=config_path, workspace_root=workspace_root)
    await system.initialize()
    yield system
    await system.shutdown()

@pytest.mark.asyncio
async def test_system_initialization(unified_system):
    """Test that the system initializes correctly."""
    assert unified_system is not None
    assert unified_system.store is not None
    assert unified_system.model_gateway is not None

@pytest.mark.asyncio
async def test_component_health(unified_system):
    """Test that components report healthy status."""
    store_health = await unified_system.store.check_health()
    gateway_health = await unified_system.model_gateway.check_health()
    assert store_health
    assert gateway_health

@pytest.mark.asyncio
async def test_model_gateway(unified_system):
    """Test that the model gateway can access providers."""
    providers = await unified_system.model_gateway.get_providers()
    assert len(providers) > 0

@pytest.mark.asyncio
async def test_pattern_store(unified_system):
    """Test pattern storage and retrieval."""
    pattern = {"type": "command", "content": "ls -l", "context": {"cwd": "/tmp"}}
    pattern_id = await unified_system.store.store_pattern(pattern)
    assert pattern_id is not None
    stored_pattern = await unified_system.store.get_pattern(pattern_id)
    assert stored_pattern["content"] == pattern["content"]

@pytest.mark.asyncio
async def test_credential_management(unified_system):
    """Test credential storage and retrieval."""
    provider = "test_provider"
    credential = "test_credential"
    await unified_system.credential_manager.store_credential(provider, credential)
    stored_credential = await unified_system.credential_manager.get_credential(provider)
    assert stored_credential == credential

@pytest.mark.asyncio
async def test_system_shutdown(unified_system):
    """Test that the system shuts down gracefully."""
    await unified_system.shutdown()
    assert not unified_system.is_running()

@pytest.mark.asyncio
async def test_error_handling(unified_system):
    """Test error handling for nonexistent patterns."""
    with pytest.raises(KeyError):
        await unified_system.store.get_pattern("nonexistent")

@pytest.mark.asyncio
async def test_component_integration(unified_system):
    """Test integration between components."""
    pattern = {"type": "command", "content": "echo test", "context": {"cwd": "/tmp"}}
    pattern_id = await unified_system.store.store_pattern(pattern)
    assert pattern_id is not None

@pytest.mark.asyncio
async def test_parallel_execution(unified_system):
    """Test parallel operations on patterns."""
    patterns = [
        {"type": "command", "content": f"test {i}", "context": {"cwd": "/tmp"}}
        for i in range(5)
    ]
    pattern_ids = await asyncio.gather(
        *[unified_system.store.store_pattern(p) for p in patterns]
    )
    assert len(pattern_ids) == 5
    assert all(pid is not None for pid in pattern_ids)

# New test cases for critical components

@pytest.mark.asyncio
async def test_safety_intermediary(unified_system):
    """Test safety intermediary functionality."""
    safety = SafetyIntermediary(unified_system.workspace_root)
    await safety.initialize()

    # Test pattern validation
    unsafe_pattern = {"type": "command", "content": "rm -rf /", "context": {}}
    is_safe = await safety.validate_pattern(unsafe_pattern)
    assert not is_safe

    safe_pattern = {"type": "command", "content": "echo test", "context": {}}
    is_safe = await safety.validate_pattern(safe_pattern)
    assert is_safe

@pytest.mark.asyncio
async def test_neural_manipulator(unified_system):
    """Test neural manipulator functionality."""
    manipulator = NeuralManipulator()
    await manipulator.initialize()

    # Test pattern transformation
    pattern = {"type": "text", "content": "test content", "context": {}}
    transformed = await manipulator.transform_pattern(pattern)
    assert transformed is not None
    assert "neural_signature" in transformed

@pytest.mark.asyncio
async def test_ai_gateway_controller(unified_system):
    """Test AI gateway controller functionality."""
    controller = AIGatewayController()
    await controller.initialize()

    # Test provider management
    providers = await controller.list_providers()
    assert len(providers) > 0

    # Test model routing
    route = await controller.get_optimal_route("code_generation")
    assert route is not None
    assert "provider" in route
    assert "model" in route

@pytest.mark.asyncio
async def test_local_ai_orchestrator(unified_system):
    """Test local AI orchestrator functionality."""
    orchestrator = LocalAIOrchestrator(unified_system.workspace_root)
    await orchestrator.initialize()

    # Test local model management
    models = await orchestrator.get_local_models()
    assert len(models) > 0

    # Test execution
    result = await orchestrator.execute_local(
        "test prompt",
        model="codellama",
        max_tokens=100
    )
    assert result is not None
    assert "content" in result

if __name__ == "__main__":
    pytest.main(["-v", "--cov=core", "--cov-report=term-missing", __file__])
