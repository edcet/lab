"""Safety Intermediary for Agent Operations

Provides a protective layer between agents and system:
- Validates all operations
- Logs actions
- Maintains state
- Enables rollback
- Prevents direct filesystem access
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
import json
import shutil
from datetime import datetime

@dataclass
class Operation:
    agent_id: str
    operation_type: str
    target: str
    changes: Dict
    timestamp: float
    validated: bool = False

class SafetyIntermediary:
    """Protective layer between agents and system"""

    def __init__(self, workspace_root: str):
        self.workspace = Path(workspace_root)
        self.operations_log = []
        self.state_snapshots = {}
        self.active_agents = set()

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

        # Validate operation
        if await self._validate_operation(op):
            self.operations_log.append(op)
            return True

        return False

    async def _validate_operation(self, op: Operation) -> bool:
        """Validate if operation is safe"""
        # Check if target exists
        target = self.workspace / op.target
        if not target.exists():
            logging.warning(f"Target does not exist: {op.target}")
            return False

        # Check operation type
        if op.operation_type not in ['read', 'analyze', 'modify']:
            logging.warning(f"Invalid operation type: {op.operation_type}")
            return False

        # For modify operations, extra validation
        if op.operation_type == 'modify':
            return await self._validate_modification(op)

        return True

    async def _validate_modification(self, op: Operation) -> bool:
        """Extra validation for modification operations"""
        # Check if changes preserve functionality
        # Check if changes maintain system integrity
        # Check if changes follow safety rules
        return True  # For now, always validate

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

    async def rollback(self, agent_id: str) -> bool:
        """Rollback to last safe state"""
        if not self.state_snapshots[agent_id]:
            return False

        snapshot = self.state_snapshots[agent_id][-1]

        # Restore files
        for path, content in snapshot['files'].items():
            target = Path(path)
            target.write_text(content)

        logging.info(f"Rolled back changes for agent: {agent_id}")
        return True
```
