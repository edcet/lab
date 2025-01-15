"""RadicalStore Implementation

Core storage system that manages patterns, state, and evolution tracking.
"""

import asyncio
from pathlib import Path
import sqlite3
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from cryptography.fernet import Fernet
import logging

@dataclass
class EvolutionConfig:
    """Configuration for evolution tracking"""
    learning_rate: str = "adaptive"  # adaptive, aggressive, conservative
    pattern_threshold: float = 0.8
    adaptation_interval: int = 100  # events between adaptations

@dataclass
class Pattern:
    """Core pattern data structure"""
    id: str
    type: str
    data: Dict
    confidence: float
    timestamp: float
    metadata: Optional[Dict] = None

class RadicalStore:
    """Central storage system for patterns, state and evolution tracking"""

    def __init__(self, db_path: Path, evolution_config: Dict = None):
        """Initialize the store

        Args:
            db_path: Path to the SQLite database
            evolution_config: Configuration for evolution tracking
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Setup encryption
        self.encryption_key = Fernet.generate_key()
        self.fernet = Fernet(self.encryption_key)

        # Initialize database
        self.db = self._setup_db()

        # Configure evolution tracking
        self.evolution_config = EvolutionConfig(
            **(evolution_config or {})
        )

        # Pattern matching cache
        self.pattern_cache = {}

        # State tracking
        self.state_history = []
        self.event_counter = 0

        self.logger = logging.getLogger(__name__)

    def _setup_db(self) -> sqlite3.Connection:
        """Setup the SQLite database"""
        db = sqlite3.connect(str(self.db_path))

        # Create tables
        db.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
            id TEXT PRIMARY KEY,
            type TEXT,
            encrypted_data BLOB,
            confidence REAL,
            timestamp REAL,
            metadata TEXT
        )
        """)

        db.execute("""
        CREATE TABLE IF NOT EXISTS state (
            id TEXT PRIMARY KEY,
            type TEXT,
            encrypted_data BLOB,
            timestamp REAL
        )
        """)

        db.execute("""
        CREATE TABLE IF NOT EXISTS evolution (
            id TEXT PRIMARY KEY,
            pattern_id TEXT,
            change_type TEXT,
            encrypted_data BLOB,
            timestamp REAL,
            FOREIGN KEY(pattern_id) REFERENCES patterns(id)
        )
        """)

        return db

    async def store(self, id: str, type: str, data: Dict,
                   metadata: Dict = None) -> str:
        """Store a new pattern or state

        Args:
            id: Unique identifier
            type: Type of data (pattern, state, etc)
            data: The data to store
            metadata: Optional metadata

        Returns:
            The ID of the stored item
        """
        # Encrypt the data
        encrypted = self.fernet.encrypt(
            json.dumps(data).encode()
        )

        timestamp = datetime.now().timestamp()

        if type == "pattern":
            confidence = data.get("confidence", 1.0)
            self.db.execute(
                """
                INSERT OR REPLACE INTO patterns
                VALUES (?,?,?,?,?,?)
                """,
                (
                    id, type, encrypted, confidence,
                    timestamp, json.dumps(metadata or {})
                )
            )
        else:
            self.db.execute(
                """
                INSERT OR REPLACE INTO state
                VALUES (?,?,?,?)
                """,
                (id, type, encrypted, timestamp)
            )

        self.db.commit()

        # Track evolution
        await self._track_evolution(id, type, data)

        return id

    async def get_matching_patterns(self, query: str,
                                  threshold: float = None) -> List[Pattern]:
        """Find patterns matching the query

        Args:
            query: The search query
            threshold: Minimum confidence threshold

        Returns:
            List of matching patterns
        """
        threshold = threshold or self.evolution_config.pattern_threshold

        # Check cache first
        cache_key = f"{query}:{threshold}"
        if cache_key in self.pattern_cache:
            return self.pattern_cache[cache_key]

        # Query database
        cursor = self.db.execute(
            """
            SELECT id, type, encrypted_data, confidence, timestamp, metadata
            FROM patterns
            WHERE confidence >= ?
            ORDER BY timestamp DESC
            """,
            (threshold,)
        )

        patterns = []
        for row in cursor:
            # Decrypt data
            decrypted = json.loads(
                self.fernet.decrypt(row[2]).decode()
            )

            pattern = Pattern(
                id=row[0],
                type=row[1],
                data=decrypted,
                confidence=row[3],
                timestamp=row[4],
                metadata=json.loads(row[5])
            )

            # Simple pattern matching for now
            # TODO: Add more sophisticated matching
            if self._matches_pattern(pattern, query):
                patterns.append(pattern)

        # Cache results
        self.pattern_cache[cache_key] = patterns

        return patterns

    async def track_evolution(self, data: Dict) -> Dict:
        """Track system evolution

        Args:
            data: Evolution data including intention, achievements etc

        Returns:
            Evolution analysis results
        """
        self.event_counter += 1

        # Store evolution data
        evolution_id = f"evolution_{datetime.now().timestamp()}"
        await self.store(
            id=evolution_id,
            type="evolution",
            data=data
        )

        # Check if we should adapt
        should_adapt = (
            self.event_counter %
            self.evolution_config.adaptation_interval == 0
        )

        if should_adapt:
            return await self._analyze_evolution()

        return {"indicates_growth": False}

    def _matches_pattern(self, pattern: Pattern, query: str) -> bool:
        """Check if pattern matches query"""
        # Simple substring matching for now
        # TODO: Add more sophisticated matching
        query = query.lower()
        return (
            query in pattern.type.lower() or
            query in json.dumps(pattern.data).lower() or
            query in json.dumps(pattern.metadata or {}).lower()
        )

    async def _track_evolution(self, id: str, type: str, data: Dict):
        """Track evolution of patterns and state"""
        if type not in ("pattern", "state"):
            return

        # Store evolution event
        evolution_id = f"evolution_{datetime.now().timestamp()}"

        encrypted = self.fernet.encrypt(
            json.dumps({
                "id": id,
                "type": type,
                "data": data,
                "timestamp": datetime.now().timestamp()
            }).encode()
        )

        self.db.execute(
            """
            INSERT INTO evolution
            VALUES (?,?,?,?,?)
            """,
            (
                evolution_id, id, type,
                encrypted, datetime.now().timestamp()
            )
        )

        self.db.commit()

    async def _analyze_evolution(self) -> Dict:
        """Analyze system evolution"""
        # Get recent evolution events
        cursor = self.db.execute(
            """
            SELECT encrypted_data
            FROM evolution
            ORDER BY timestamp DESC
            LIMIT 100
            """
        )

        events = []
        for row in cursor:
            decrypted = json.loads(
                self.fernet.decrypt(row[0]).decode()
            )
            events.append(decrypted)

        # Simple growth detection for now
        # TODO: Add more sophisticated analysis
        indicates_growth = len(events) >= 10

        return {
            "indicates_growth": indicates_growth,
            "events_analyzed": len(events),
            "timestamp": datetime.now().timestamp()
        }
