"""Distributed State Management System with synchronization and persistence"""

import asyncio
from typing import Dict, Any, Optional, List, Set, Union
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
import json
import pickle
from pathlib import Path
import sqlite3
from contextlib import asynccontextmanager
import hashlib
import time

@dataclass
class SystemState:
    """Core system state"""
    version: str
    start_time: datetime
    components: Dict[str, bool]  # Component status
    models: Dict[str, Dict]      # Model states
    tools: Dict[str, Dict]       # Tool states
    memory: Dict[str, float]     # Memory usage
    tasks: Dict[str, Dict]       # Active tasks
    errors: List[Dict]           # Recent errors
    metrics: Dict[str, Any]      # Performance metrics

@dataclass
class StateSnapshot:
    """Point-in-time state snapshot"""
    id: str
    timestamp: datetime
    state: SystemState
    checksum: str

class StateManager:
    """Manages system state with persistence and synchronization"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.state = SystemState(
            version="0.1.0",
            start_time=datetime.now(),
            components={},
            models={},
            tools={},
            memory={},
            tasks={},
            errors=[],
            metrics={}
        )
        self.snapshot_interval = 60  # 1 minute
        self.max_snapshots = 100
        self.state_lock = asyncio.Lock()
        self.db_conn = None
        self.logger = logging.getLogger(__name__)
        
        # Change tracking
        self.pending_changes = set()
        self.last_snapshot = None
        
        # Recovery points
        self.recovery_points = {}

    async def initialize(self) -> bool:
        """Initialize state management"""
        try:
            # Create storage directory
            self.storage_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            await self._initialize_db()
            
            # Load last known state
            await self._load_last_state()
            
            # Start background tasks
            asyncio.create_task(self._auto_snapshot())
            asyncio.create_task(self._cleanup_old_snapshots())
            
            self.logger.info("State Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"State initialization failed: {e}")
            return False

    async def _initialize_db(self):
        """Initialize SQLite database"""
        db_path = self.storage_path / "state.db"
        self.db_conn = sqlite3.connect(str(db_path))
        
        # Create tables
        with self.db_conn:
            self.db_conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    state BLOB,
                    checksum TEXT
                )
            """)
            
            self.db_conn.execute("""
                CREATE TABLE IF NOT EXISTS recovery_points (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    state BLOB,
                    metadata TEXT
                )
            """)

    async def _load_last_state(self):
        """Load last known state from database"""
        with self.db_conn:
            cursor = self.db_conn.execute("""
                SELECT state FROM snapshots 
                ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            
            if row:
                state_data = pickle.loads(row[0])
                self.state = SystemState(**state_data)
                self.logger.info("Loaded previous state")

    @asynccontextmanager
    async def state_transaction(self):
        """Context manager for state modifications"""
        async with self.state_lock:
            try:
                yield self.state
                # Track changes
                self.pending_changes.add(datetime.now().timestamp())
            except Exception as e:
                self.logger.error(f"State transaction error: {e}")
                raise

    async def update_component_state(self, 
                                 component: str, 
                                 status: bool):
        """Update component status"""
        async with self.state_transaction() as state:
            state.components[component] = status

    async def update_model_state(self, 
                              model: str, 
                              state_update: Dict):
        """Update model state"""
        async with self.state_transaction() as state:
            if model not in state.models:
                state.models[model] = {}
            state.models[model].update(state_update)

    async def update_tool_state(self, 
                             tool: str, 
                             state_update: Dict):
        """Update tool state"""
        async with self.state_transaction() as state:
            if tool not in state.tools:
                state.tools[tool] = {}
            state.tools[tool].update(state_update)

    async def update_memory_state(self, 
                               usage: Dict[str, float]):
        """Update memory usage state"""
        async with self.state_transaction() as state:
            state.memory.update(usage)

    async def add_task(self, 
                    task_id: str, 
                    task_info: Dict):
        """Add task to state"""
        async with self.state_transaction() as state:
            state.tasks[task_id] = {
                **task_info,
                'start_time': datetime.now().isoformat()
            }

    async def remove_task(self, task_id: str):
        """Remove task from state"""
        async with self.state_transaction() as state:
            state.tasks.pop(task_id, None)

    async def add_error(self, error: Dict):
        """Add error to state"""
        async with self.state_transaction() as state:
            state.errors.append({
                **error,
                'timestamp': datetime.now().isoformat()
            })
            # Keep only recent errors
            state.errors = state.errors[-100:]

    async def update_metrics(self, metrics: Dict):
        """Update performance metrics"""
        async with self.state_transaction() as state:
            state.metrics.update(metrics)

    async def create_snapshot(self) -> str:
        """Create state snapshot"""
        async with self.state_lock:
            # Serialize state
            state_data = asdict(self.state)
            serialized = pickle.dumps(state_data)
            
            # Generate checksum
            checksum = hashlib.sha256(serialized).hexdigest()
            
            # Create snapshot
            snapshot_id = f"snapshot_{int(time.time())}"
            snapshot = StateSnapshot(
                id=snapshot_id,
                timestamp=datetime.now(),
                state=self.state,
                checksum=checksum
            )
            
            # Store snapshot
            with self.db_conn:
                self.db_conn.execute(
                    "INSERT INTO snapshots VALUES (?, ?, ?, ?)",
                    (
                        snapshot.id,
                        snapshot.timestamp.isoformat(),
                        serialized,
                        checksum
                    )
                )
            
            self.last_snapshot = snapshot
            return snapshot_id

    async def create_recovery_point(self, 
                                 metadata: Optional[Dict] = None) -> str:
        """Create recovery point"""
        async with self.state_lock:
            # Serialize current state
            state_data = asdict(self.state)
            serialized = pickle.dumps(state_data)
            
            # Create recovery point
            recovery_id = f"recovery_{int(time.time())}"
            
            # Store recovery point
            with self.db_conn:
                self.db_conn.execute(
                    "INSERT INTO recovery_points VALUES (?, ?, ?, ?)",
                    (
                        recovery_id,
                        datetime.now().isoformat(),
                        serialized,
                        json.dumps(metadata or {})
                    )
                )
            
            self.recovery_points[recovery_id] = datetime.now()
            return recovery_id

    async def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore state from snapshot"""
        try:
            with self.db_conn:
                cursor = self.db_conn.execute(
                    "SELECT state, checksum FROM snapshots WHERE id = ?",
                    (snapshot_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    raise ValueError(f"Snapshot {snapshot_id} not found")
                
                serialized, stored_checksum = row
                
                # Verify checksum
                checksum = hashlib.sha256(serialized).hexdigest()
                if checksum != stored_checksum:
                    raise ValueError("Snapshot checksum mismatch")
                
                # Restore state
                async with self.state_lock:
                    state_data = pickle.loads(serialized)
                    self.state = SystemState(**state_data)
                
                self.logger.info(f"Restored state from snapshot {snapshot_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Snapshot restoration failed: {e}")
            return False

    async def restore_recovery_point(self, 
                                  recovery_id: str) -> bool:
        """Restore state from recovery point"""
        try:
            with self.db_conn:
                cursor = self.db_conn.execute(
                    "SELECT state FROM recovery_points WHERE id = ?",
                    (recovery_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    raise ValueError(f"Recovery point {recovery_id} not found")
                
                # Restore state
                async with self.state_lock:
                    state_data = pickle.loads(row[0])
                    self.state = SystemState(**state_data)
                
                self.logger.info(f"Restored state from recovery point {recovery_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Recovery point restoration failed: {e}")
            return False

    async def _auto_snapshot(self):
        """Automatically create snapshots"""
        while True:
            try:
                if self.pending_changes:
                    await self.create_snapshot()
                    self.pending_changes.clear()
                
                await asyncio.sleep(self.snapshot_interval)
            except Exception as e:
                self.logger.error(f"Auto snapshot error: {e}")
                await asyncio.sleep(self.snapshot_interval * 2)

    async def _cleanup_old_snapshots(self):
        """Clean up old snapshots"""
        while True:
            try:
                with self.db_conn:
                    # Keep only last max_snapshots
                    self.db_conn.execute("""
                        DELETE FROM snapshots WHERE id NOT IN (
                            SELECT id FROM snapshots 
                            ORDER BY timestamp DESC 
                            LIMIT ?
                        )
                    """, (self.max_snapshots,))
                    
                    # Clean old recovery points (older than 24 hours)
                    self.db_conn.execute("""
                        DELETE FROM recovery_points 
                        WHERE datetime(timestamp) < datetime('now', '-1 day')
                    """)
                
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(7200)

    async def get_state(self) -> SystemState:
        """Get current state"""
        async with self.state_lock:
            return self.state

    async def get_metrics(self) -> Dict[str, Any]:
        """Get state manager metrics"""
        async with self.state_lock:
            return {
                'components': len(self.state.components),
                'active_tasks': len(self.state.tasks),
                'error_count': len(self.state.errors),
                'last_snapshot': self.last_snapshot.timestamp.isoformat()
                if self.last_snapshot else None,
                'recovery_points': len(self.recovery_points),
                'pending_changes': len(self.pending_changes)
            }

    async def cleanup(self):
        """Cleanup state management"""
        try:
            # Create final snapshot
            if self.pending_changes:
                await self.create_snapshot()
            
            # Close database connection
            if self.db_conn:
                self.db_conn.close()
            
            self.logger.info("State Manager cleanup completed")
        except Exception as e:
            self.logger.error(f"State cleanup error: {e}")
            raise
