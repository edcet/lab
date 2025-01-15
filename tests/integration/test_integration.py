import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from src.utils.integration_orchestrator import *

class AsyncResourceTracker:
    def __init__(self):
        self._resources = set()
        self._task_groups = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    def register_system(self, system):
        self._resources.add(system)

    async def cleanup(self):
        for resource in self._resources:
            if hasattr(resource, '_background_tasks'):
                for task in resource._background_tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*resource._background_tasks, return_exceptions=True)

@pytest_asyncio.fixture(scope="session")
async def unified_system():
    """Create an optimized UnifiedSystem instance for testing."""
    from unified_system import UnifiedSystem
    system = None
    try:
        system = UnifiedSystem(
            config_path=Path(".test_workspace/.config/system/config.json"),
            workspace_root=Path(".test_workspace")
        )

        async with AsyncResourceTracker() as tracker:
            await system.initialize()
            tracker.register_system(system)
            yield system

    finally:
        if system and hasattr(system, '_initialized') and system._initialized:
            async with AsyncResourceTracker() as tracker:
                await system.shutdown()
                await tracker.cleanup()

@pytest.mark.asyncio
async def test_system_initialization(unified_system):
    """Test that the system initializes correctly."""
    assert unified_system is not None
    assert unified_system.store is not None
    assert unified_system.model_gateway is not None
    assert unified_system.safety_system is not None
    assert unified_system.state_manager is not None

@pytest.mark.asyncio
async def test_state_management(unified_system):
    """Test state management functionality."""
    # Test state transitions
    initial_state = {"version": "1.0", "timestamp": time.time(), "checksum": "abc"}
    new_state = {"version": "1.0", "timestamp": time.time(), "checksum": "def"}

    # Monitor state transition
    assert await unified_system.safety_system.monitor_state_transition(initial_state, new_state)

    # Test invalid state transition
    invalid_state = {"version": "1.0"}  # Missing required fields
    assert not await unified_system.safety_system.monitor_state_transition(initial_state, invalid_state)

@pytest.mark.asyncio
async def test_critical_operations(unified_system):
    """Test critical operations handling."""
    context = SecurityContext(
        request_id="test_op",
        timestamp=datetime.now(),
        source="test",
        critical=True
    )

    async with unified_system.safety_system.critical_operation("test_op", context):
        # Perform critical operation
        state = {"version": "1.0", "timestamp": time.time(), "checksum": "abc"}
        assert await unified_system.safety_system.monitor_state_transition({}, state)

@pytest.mark.asyncio
async def test_security_validation(unified_system):
    """Test security validation functionality."""
    context = SecurityContext(
        request_id="test_req",
        timestamp=datetime.now(),
        source="test"
    )

    # Test valid request
    assert await unified_system.safety_system.validate_request("valid content", context)

    # Test rate limiting
    for _ in range(unified_system.safety_system.policy.max_requests_per_minute + 1):
        await unified_system.safety_system.validate_request("test", context)
    assert not await unified_system.safety_system.validate_request("rate limited", context)

@pytest.mark.asyncio
async def test_encryption(unified_system):
    """Test encryption functionality."""
    sensitive_data = "sensitive information"
    encrypted = unified_system.safety_system.encrypt_sensitive(sensitive_data)
    decrypted = unified_system.safety_system.decrypt_sensitive(encrypted)
    assert decrypted == sensitive_data

@pytest.mark.asyncio
async def test_audit_logging(unified_system):
    """Test audit logging functionality."""
    context = SecurityContext(
        request_id="test_audit",
        timestamp=datetime.now(),
        source="test"
    )
    await unified_system.safety_system.audit_log(
        "test_event",
        context,
        {"detail": "test"}
    )
    assert Path("audit.log").exists()

@pytest.mark.asyncio
async def test_component_health(unified_system):
    """Test that components report healthy status."""
    assert await unified_system.store.check_health()
    assert await unified_system.model_gateway.check_health()
    assert await unified_system.safety_system.monitor_security()

@pytest.mark.asyncio
async def test_pattern_store(unified_system):
    """Test pattern storage and retrieval."""
    pattern = {
        "type": "command",
        "content": "ls -l",
        "context": {"cwd": "/tmp"}
    }
    pattern_id = await unified_system.store.store_pattern(pattern)
    assert pattern_id is not None
    stored_pattern = await unified_system.store.get_pattern(pattern_id)
    assert stored_pattern["content"] == pattern["content"]

@pytest.mark.asyncio
async def test_forced_shutdown(unified_system):
    """Test system behavior during forced shutdown."""
    # Setup test state
    state = {"version": "1.0", "timestamp": time.time(), "checksum": "abc"}
    await unified_system.state_manager._update_state(state)

    # Simulate forced shutdown
    await unified_system.state_manager._async_shutdown()

    # Verify state was saved
    assert Path(unified_system.state_manager.config.persistence_path).exists()

    # Verify cleanup
    assert not unified_system.state_manager._save_task.is_running()

@pytest.mark.asyncio
async def test_parallel_operations(unified_system):
    """Test parallel operations with state management."""
    async def operation(i: int):
        context = SecurityContext(
            request_id=f"test_op_{i}",
            timestamp=datetime.now(),
            source="test"
        )
        async with unified_system.safety_system.critical_operation(f"op_{i}", context):
            state = {
                "version": "1.0",
                "timestamp": time.time(),
                "checksum": f"test_{i}",
                "data": f"value_{i}"
            }
            return await unified_system.safety_system.monitor_state_transition({}, state)

    # Run multiple operations in parallel
    results = await asyncio.gather(*[operation(i) for i in range(5)])
    assert all(results)  # All operations should succeed
