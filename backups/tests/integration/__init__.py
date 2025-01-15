"""Integration tests for quantum path system."""

import os
import json
import time
import pytest
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import stat
from unittest.mock import patch

class QuantumPathTester:
    """Test harness for quantum path system."""

    def __init__(self, state_dir: Optional[Path] = None):
        """Initialize test harness."""
        self.state_dir = state_dir or Path(os.environ.get('XDG_STATE_HOME',
                                         Path.home() / '.local/state')) / 'quantum-path'
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def read_state(self) -> Dict:
        """Read current quantum state."""
        state_file = self.state_dir / 'quantum.db'
        if not state_file.exists():
            return {}
        return json.loads(state_file.read_text())

    def read_metrics(self) -> Dict:
        """Read performance metrics."""
        metrics_file = self.state_dir / 'metrics.json'
        if not metrics_file.exists():
            return {}
        return json.loads(metrics_file.read_text())

    def simulate_shell(self, commands: List[str]) -> subprocess.CompletedProcess:
        """Simulate shell execution."""
        env = os.environ.copy()
        env['ZDOTDIR'] = str(Path.home() / '.config/zsh')
        return subprocess.run(
            ['zsh', '-c', '; '.join(commands)],
            env=env,
            capture_output=True,
            text=True
        )

    def verify_isolation(self, context: str) -> bool:
        """Verify context isolation."""
        state = self.read_state()
        return all(
            ctx.endswith('_isolated')
            for ctx in state.get('isolation', {}).keys()
            if ctx.startswith(context)
        )

    def verify_locks(self) -> bool:
        """Verify no orphaned locks."""
        locks_dir = self.state_dir / 'locks'
        if not locks_dir.exists():
            return True
        return len(list(locks_dir.glob('*.lock'))) == 0

    def verify_recovery_points(self) -> bool:
        """Verify recovery points exist."""
        recovery_dir = self.state_dir / 'recovery'
        if not recovery_dir.exists():
            return False
        points = list(recovery_dir.glob('state_*'))
        return len(points) <= 5 and len(points) > 0

@pytest.fixture
def quantum_tester():
    """Provide test harness."""
    return QuantumPathTester()

def test_basic_isolation(quantum_tester):
    """Test basic context isolation."""
    result = quantum_tester.simulate_shell([
        'cd /tmp',
        'python3 -m venv test_venv',
        'source test_venv/bin/activate',
        'echo $PATH'
    ])
    assert quantum_tester.verify_isolation('venv')

def test_concurrent_shells(quantum_tester):
    """Test concurrent shell handling."""
    shell1 = quantum_tester.simulate_shell(['echo $PATH'])
    shell2 = quantum_tester.simulate_shell(['echo $PATH'])
    assert quantum_tester.verify_locks()

def test_recovery_points(quantum_tester):
    """Test recovery point creation."""
    for _ in range(10):
        quantum_tester.simulate_shell(['cd /tmp'])
        time.sleep(0.1)
    assert quantum_tester.verify_recovery_points()

def test_performance_metrics(quantum_tester):
    """Test performance monitoring."""
    quantum_tester.simulate_shell(['cd /tmp'] * 100)
    metrics = quantum_tester.read_metrics()
    assert 'last_sync_duration' in metrics
    assert 'last_opt_duration' in metrics

def test_path_safety(quantum_tester):
    """Test path safety verification."""
    # Test whitelisted path
    result = quantum_tester.simulate_shell([
        'echo $PATH',
        'test -d /usr/local/bin && echo "safe" || echo "unsafe"'
    ])
    assert 'safe' in result.stdout

    # Test unsafe path
    unsafe_path = '/tmp/unsafe_test'
    result = quantum_tester.simulate_shell([
        f'mkdir -p {unsafe_path}',
        f'chmod 777 {unsafe_path}',
        f'test -d {unsafe_path} && echo $PATH',
        f'rm -rf {unsafe_path}'
    ])
    assert 'Unsafe path detected' in result.stderr

    # Test permission checks
    with patch('os.stat') as mock_stat:
        mock_stat.return_value.st_mode = stat.S_IFDIR | 0o777
        mock_stat.return_value.st_uid = os.getuid()
        result = quantum_tester.simulate_shell(['echo $PATH'])
        assert 'Invalid permissions' in result.stderr

    # Test ownership checks
    with patch('os.stat') as mock_stat:
        mock_stat.return_value.st_mode = stat.S_IFDIR | 0o755
        mock_stat.return_value.st_uid = os.getuid() + 1
        result = quantum_tester.simulate_shell(['echo $PATH'])
        assert 'Invalid ownership' in result.stderr

def test_path_whitelist(quantum_tester):
    """Test path whitelist functionality."""
    # Test system paths
    for path in ['/usr/local/bin', '/usr/bin', '/bin']:
        result = quantum_tester.simulate_shell([
            f'test -d {path} && echo $PATH'
        ])
        assert 'Unsafe path detected' not in result.stderr

    # Test user paths
    home = os.path.expanduser('~')
    for path in ['.local/bin', '.cargo/bin']:
        result = quantum_tester.simulate_shell([
            f'mkdir -p {home}/{path}',
            f'test -d {home}/{path} && echo $PATH',
            f'rm -rf {home}/{path}'
        ])
        assert 'Unsafe path detected' not in result.stderr

def test_path_isolation(quantum_tester):
    """Test path isolation with safety."""
    # Test venv isolation
    result = quantum_tester.simulate_shell([
        'cd /tmp',
        'python3 -m venv test_venv',
        'source test_venv/bin/activate',
        'echo $PATH',
        'deactivate',
        'rm -rf test_venv'
    ])
    assert quantum_tester.verify_isolation('venv')
    assert 'Unsafe path detected' not in result.stderr

    # Test git isolation
    result = quantum_tester.simulate_shell([
        'cd /tmp',
        'git init test_repo',
        'cd test_repo',
        'echo $PATH',
        'cd ..',
        'rm -rf test_repo'
    ])
    assert quantum_tester.verify_isolation('git')
    assert 'Unsafe path detected' not in result.stderr
