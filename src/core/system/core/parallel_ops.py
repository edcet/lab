"""Advanced parallel operations management system."""

import time
import heapq
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

@dataclass
class Operation:
    """Parallel operation with tracking"""
    id: str
    type: str
    priority: int
    resources: Dict[str, float]
    start_time: datetime = datetime.now()
    end_time: Optional[datetime] = None
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None

class ParallelOpsManager:
    """Advanced parallel operations management"""

    def __init__(self):
        self.active_ops: Dict[str, Operation] = {}
        self.completed_ops: List[Operation] = []
        self.op_history: List[Dict] = []
        self.max_parallel_ops = 10
        self.priority_queue = []
        self.resource_limits = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0
        }
        self.current_resources = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0
        }

    async def start_operation(self, op_type: str, priority: int, resources: Dict[str, float]) -> Optional[str]:
        """Start new parallel operation with resource check"""
        try:
            # Generate operation ID
            op_id = f"{op_type}_{len(self.op_history)}_{int(time.time())}"

            # Create operation
            operation = Operation(
                id=op_id,
                type=op_type,
                priority=priority,
                resources=resources
            )

            # Check resources and limits
            if not self._can_start_operation(operation):
                # Add to priority queue
                heapq.heappush(self.priority_queue, (-priority, op_id, operation))
                return None

            # Start operation
            self.active_ops[op_id] = operation
            self._update_resources(operation, add=True)
            self._record_history("start", operation)

            return op_id

        except Exception as e:
            logging.error(f"Error starting operation: {e}")
            return None

    async def complete_operation(self, op_id: str, result: Any = None, error: Optional[str] = None):
        """Complete parallel operation"""
        if op_id not in self.active_ops:
            return

        operation = self.active_ops[op_id]
        operation.end_time = datetime.now()
        operation.status = "error" if error else "completed"
        operation.result = result
        operation.error = error

        # Update resources
        self._update_resources(operation, add=False)

        # Move to completed
        self.completed_ops.append(operation)
        del self.active_ops[op_id]

        # Record history
        self._record_history("complete", operation)

        # Check queue
        await self._process_queue()

    def _can_start_operation(self, operation: Operation) -> bool:
        """Check if operation can start"""
        # Check parallel limit
        if len(self.active_ops) >= self.max_parallel_ops:
            return False

        # Check resources
        for resource, required in operation.resources.items():
            if resource in self.resource_limits:
                if self.current_resources[resource] + required > self.resource_limits[resource]:
                    return False

        return True

    def _update_resources(self, operation: Operation, add: bool):
        """Update resource tracking"""
        factor = 1 if add else -1
        for resource, amount in operation.resources.items():
            if resource in self.current_resources:
                self.current_resources[resource] += amount * factor

    async def _process_queue(self):
        """Process queued operations"""
        while self.priority_queue:
            # Check next operation
            _, op_id, operation = self.priority_queue[0]

            if self._can_start_operation(operation):
                # Start operation
                heapq.heappop(self.priority_queue)
                await self.start_operation(
                    operation.type,
                    operation.priority,
                    operation.resources
                )
            else:
                break

    def _record_history(self, action: str, operation: Operation):
        """Record operation history"""
        self.op_history.append({
            "timestamp": datetime.now(),
            "action": action,
            "operation": {
                "id": operation.id,
                "type": operation.type,
                "priority": operation.priority,
                "resources": operation.resources,
                "status": operation.status,
                "duration": (operation.end_time - operation.start_time).total_seconds() if operation.end_time else None
            }
        })

        # Trim history if needed
        if len(self.op_history) > 1000:
            self.op_history = self.op_history[-1000:]

    def get_active_operations(self) -> List[Operation]:
        """Get currently active operations"""
        return list(self.active_ops.values())

    def get_operation_stats(self) -> Dict[str, Any]:
        """Get operation statistics"""
        stats = {
            "active_count": len(self.active_ops),
            "queued_count": len(self.priority_queue),
            "completed_count": len(self.completed_ops),
            "resource_usage": self.current_resources.copy(),
            "resource_limits": self.resource_limits.copy(),
            "operation_types": defaultdict(int),
            "average_duration": 0.0,
            "error_rate": 0.0
        }

        # Calculate operation type distribution
        for op in self.completed_ops:
            stats["operation_types"][op.type] += 1

        # Calculate average duration and error rate
        if self.completed_ops:
            durations = [
                (op.end_time - op.start_time).total_seconds()
                for op in self.completed_ops
                if op.end_time
            ]
            if durations:
                stats["average_duration"] = sum(durations) / len(durations)

            error_count = sum(1 for op in self.completed_ops if op.error)
            stats["error_rate"] = error_count / len(self.completed_ops)

        return stats

    def is_safe(self) -> bool:
        """Enhanced safety check for parallel operations"""
        stats = self.get_operation_stats()

        return all([
            stats["active_count"] < self.max_parallel_ops,
            stats["error_rate"] < 0.2,
            all(usage < limit * 0.9 for usage, limit in zip(
                self.current_resources.values(),
                self.resource_limits.values()
            ))
        ])

    async def cancel_operation(self, op_id: str):
        """Cancel an active operation"""
        if op_id in self.active_ops:
            operation = self.active_ops[op_id]
            operation.status = "cancelled"
            operation.end_time = datetime.now()
            self._update_resources(operation, add=False)
            self.completed_ops.append(operation)
            del self.active_ops[op_id]
            self._record_history("cancel", operation)

    async def pause_operation(self, op_id: str):
        """Pause an active operation"""
        if op_id in self.active_ops:
            operation = self.active_ops[op_id]
            operation.status = "paused"
            self._update_resources(operation, add=False)
            self._record_history("pause", operation)

    async def resume_operation(self, op_id: str):
        """Resume a paused operation"""
        if op_id in self.active_ops:
            operation = self.active_ops[op_id]
            if operation.status == "paused":
                operation.status = "running"
                self._update_resources(operation, add=True)
                self._record_history("resume", operation)

    def cleanup_old_operations(self, max_age_hours: int = 24):
        """Clean up old completed operations"""
        now = datetime.now()
        self.completed_ops = [
            op for op in self.completed_ops
            if (now - op.end_time).total_seconds() < max_age_hours * 3600
        ]
