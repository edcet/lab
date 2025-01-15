#!/usr/bin/env python3

"""Safety intermediary for the excavation system"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

@dataclass
class SafetyCheck:
    """Represents a safety check result"""
    passed: bool
    reason: str
    timestamp: float
    context: Dict

@dataclass
class Operation:
    """Represents a system operation"""
    id: str
    agent_id: str
    operation_type: str
    target: str
    changes: Dict
    timestamp: float
    validated: bool = False

class ExcavationSafety:
    """Safety system for excavation operations"""

    def __init__(self, workspace_root: str):
        self.workspace = Path(workspace_root)
        self.operations_log = []
        self.state_snapshots = {}
        self.active_agents = set()
        self.safety_checks = {
            "filesystem": self._check_filesystem_safety,
            "resources": self._check_resource_safety,
            "integration": self._check_integration_safety,
            "emergence": self._check_emergence_safety
        }

        # Setup logging
        logging.basicConfig(
            filename='safety.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    async def register_agent(self, agent_id: str, capabilities: List[str]) -> bool:
        """Register an agent with specific capabilities"""
        if agent_id in self.active_agents:
            return False

        logging.info(f"Registering agent: {agent_id} with caps: {capabilities}")
        self.active_agents.add(agent_id)
        self.state_snapshots[agent_id] = []
        return True

    async def request_operation(self, agent_id: str, operation: Dict) -> bool:
        """Request permission for an operation"""
        if agent_id not in self.active_agents:
            logging.warning(f"Unregistered agent {agent_id} attempted operation")
            return False

        op = Operation(
            id=operation.get('id', str(len(self.operations_log))),
            agent_id=agent_id,
            operation_type=operation['type'],
            target=operation['target'],
            changes=operation['changes'],
            timestamp=datetime.now().timestamp()
        )

        # Log the request
        logging.info(f"Operation requested: {op}")

        # Take state snapshot
        await self._take_snapshot(agent_id)

        # Run all safety checks
        check_results = await self._run_safety_checks(op)

        if all(check.passed for check in check_results):
            self.operations_log.append(op)
            return True

        # Log failed checks
        for check in check_results:
            if not check.passed:
                logging.warning(f"Safety check failed: {check.reason}")

        return False

    async def _run_safety_checks(self, op: Operation) -> List[SafetyCheck]:
        """Run all safety checks for an operation"""
        results = []
        for check_name, check_func in self.safety_checks.items():
            try:
                result = await check_func(op)
                results.append(result)
            except Exception as e:
                logging.error(f"Safety check {check_name} failed: {e}")
                results.append(SafetyCheck(
                    passed=False,
                    reason=f"Check failed: {str(e)}",
                    timestamp=datetime.now().timestamp(),
                    context={"error": str(e)}
                ))
        return results

    async def _check_filesystem_safety(self, op: Operation) -> SafetyCheck:
        """Check if filesystem operations are safe"""
        target = self.workspace / op.target

        # Verify target exists and is within workspace
        if not str(target).startswith(str(self.workspace)):
            return SafetyCheck(
                passed=False,
                reason="Target outside workspace",
                timestamp=datetime.now().timestamp(),
                context={"target": str(target)}
            )

        # Check operation type
        if op.operation_type not in ['read', 'analyze', 'modify']:
            return SafetyCheck(
                passed=False,
                reason="Invalid operation type",
                timestamp=datetime.now().timestamp(),
                context={"type": op.operation_type}
            )

        return SafetyCheck(
            passed=True,
            reason="Filesystem checks passed",
            timestamp=datetime.now().timestamp(),
            context={"target": str(target)}
        )

    async def _check_resource_safety(self, op: Operation) -> SafetyCheck:
        """Check if operation is safe for system resources"""
        # Check memory usage
        mem_usage = psutil.virtual_memory().percent
        if mem_usage > 90:  # 90% memory usage threshold
            return SafetyCheck(
                passed=False,
                reason="Memory usage too high",
                timestamp=datetime.now().timestamp(),
                context={"memory_usage": mem_usage}
            )

        # Check CPU usage
        cpu_usage = psutil.cpu_percent()
        if cpu_usage > 80:  # 80% CPU usage threshold
            return SafetyCheck(
                passed=False,
                reason="CPU usage too high",
                timestamp=datetime.now().timestamp(),
                context={"cpu_usage": cpu_usage}
            )

        return SafetyCheck(
            passed=True,
            reason="Resource checks passed",
            timestamp=datetime.now().timestamp(),
            context={"memory": mem_usage, "cpu": cpu_usage}
        )

    async def _check_integration_safety(self, op: Operation) -> SafetyCheck:
        """Check if operation is safe for system integration"""
        # Check for conflicts with other operations
        for logged_op in self.operations_log[-10:]:  # Check last 10 operations
            if logged_op.target == op.target and logged_op.id != op.id:
                # Check timestamp to avoid race conditions
                if abs(logged_op.timestamp - op.timestamp) < 5:  # 5 second window
                    return SafetyCheck(
                        passed=False,
                        reason="Operation conflict detected",
                        timestamp=datetime.now().timestamp(),
                        context={"conflict_with": logged_op.id}
                    )

        return SafetyCheck(
            passed=True,
            reason="Integration checks passed",
            timestamp=datetime.now().timestamp(),
            context={}
        )

    async def _check_emergence_safety(self, op: Operation) -> SafetyCheck:
        """Check for dangerous emergent behavior"""
        # Analyze operation patterns
        recent_ops = [o for o in self.operations_log[-20:]
                     if o.agent_id == op.agent_id]

        # Check for rapid repeated operations
        if len(recent_ops) > 10:
            time_window = recent_ops[-1].timestamp - recent_ops[0].timestamp
            if time_window < 5:  # More than 10 ops in 5 seconds
                return SafetyCheck(
                    passed=False,
                    reason="Too many operations too quickly",
                    timestamp=datetime.now().timestamp(),
                    context={"time_window": time_window}
                )

        return SafetyCheck(
            passed=True,
            reason="Emergence checks passed",
            timestamp=datetime.now().timestamp(),
            context={"recent_ops": len(recent_ops)}
        )

    async def _take_snapshot(self, agent_id: str):
        """Take a snapshot of current state"""
        snapshot = {
            'timestamp': datetime.now().timestamp(),
            'files': {}
        }

        # Snapshot relevant files
        for target in self.workspace.rglob('*.py'):
            if target.is_file():
                snapshot['files'][str(target)] = target.read_text()

        self.state_snapshots[agent_id].append(snapshot)

        # Keep only last 5 snapshots
        if len(self.state_snapshots[agent_id]) > 5:
            self.state_snapshots[agent_id].pop(0)

    async def start_monitoring(self):
        """Start continuous safety monitoring"""
        while True:
            try:
                # Monitor system state
                await self._monitor_system_state()

                # Clean up old logs
                await self._cleanup_old_logs()

                # Run periodic safety checks
                await self._run_periodic_checks()

                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Safety monitoring error: {e}")
                await asyncio.sleep(5)  # Back off on error

    async def _monitor_system_state(self):
        """Monitor overall system state"""
        # Check active agents
        for agent_id in list(self.active_agents):
            last_op = next(
                (op for op in reversed(self.operations_log)
                 if op.agent_id == agent_id),
                None
            )
            if last_op and (datetime.now().timestamp() - last_op.timestamp) > 300:
                logging.warning(f"Agent {agent_id} appears inactive")

    async def _cleanup_old_logs(self):
        """Clean up old operation logs"""
        current_time = datetime.now().timestamp()
        # Keep only last 24 hours of logs
        self.operations_log = [
            op for op in self.operations_log
            if (current_time - op.timestamp) < 86400
        ]

    async def _run_periodic_checks(self):
        """Run periodic safety checks"""
        # Check for patterns that might indicate issues
        op_count = len(self.operations_log)
        if op_count > 1000:
            logging.warning("High operation count detected")

async def main():
    safety = ExcavationSafety("/Users/him/lab")
    await safety.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
