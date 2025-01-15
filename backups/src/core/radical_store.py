"""Radical Store - Central State and Pattern Management System

This module implements the RadicalStore class which serves as a central system for:
1. Pattern storage and evolution tracking
2. State management and persistence
3. Secure data storage with encryption
4. Learning and adaptation
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
import json
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet
import numpy as np

@dataclass
class EvolutionConfig:
    """Configuration for pattern evolution"""
    learning_rate: str = "adaptive"  # adaptive, fixed, or dynamic
    pattern_threshold: float = 0.75
    max_patterns: int = 1000
    prune_frequency: int = 100

@dataclass
class Pattern:
    """Represents a detected pattern"""
    id: str
    type: str
    content: Dict[str, Any]
    context: Dict[str, Any]
    confidence: float
    created_at: datetime
    updated_at: datetime
    usage_count: int
    impact_score: float

class RadicalStore:
    """Central state and pattern management system"""

    def __init__(self, db_path: str = "~/.radical/store.db", evolution_config: Optional[Dict] = None):
        """Initialize the RadicalStore

        Args:
            db_path: Path to the SQLite database
            evolution_config: Configuration for pattern evolution
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Setup encryption
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

        # Initialize evolution config
        self.evolution_config = EvolutionConfig(**(evolution_config or {}))

        # Setup database
        self._setup_db()

        # Initialize caches
        self.pattern_cache = {}
        self.state_cache = {}

        # Metrics
        self.metrics = {
            "patterns_stored": 0,
            "patterns_evolved": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }

    def _setup_db(self):
        """Setup the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Create tables
        c.execute('''
        CREATE TABLE IF NOT EXISTS patterns (
            id TEXT PRIMARY KEY,
            type TEXT,
            content BLOB,
            context BLOB,
            confidence REAL,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            usage_count INTEGER,
            impact_score REAL
        )''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS states (
            id TEXT PRIMARY KEY,
            component TEXT,
            state BLOB,
            timestamp TIMESTAMP
        )''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS evolution_events (
            id TEXT PRIMARY KEY,
            pattern_id TEXT,
            event_type TEXT,
            details BLOB,
            timestamp TIMESTAMP,
            FOREIGN KEY(pattern_id) REFERENCES patterns(id)
        )''')

        conn.commit()
        conn.close()

    async def store_pattern(self, pattern_type: str, content: Dict, context: Dict) -> str:
        """Store a new pattern

        Args:
            pattern_type: Type of pattern
            content: Pattern content
            context: Pattern context

        Returns:
            str: Pattern ID
        """
        pattern = Pattern(
            id=self._generate_id(),
            type=pattern_type,
            content=content,
            context=context,
            confidence=0.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            usage_count=0,
            impact_score=0.0
        )

        # Encrypt sensitive data
        encrypted_content = self.cipher.encrypt(json.dumps(content).encode())
        encrypted_context = self.cipher.encrypt(json.dumps(context).encode())

        # Store in database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
        INSERT INTO patterns
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern.id,
            pattern.type,
            encrypted_content,
            encrypted_context,
            pattern.confidence,
            pattern.created_at,
            pattern.updated_at,
            pattern.usage_count,
            pattern.impact_score
        ))
        conn.commit()
        conn.close()

        # Update cache
        self.pattern_cache[pattern.id] = pattern
        self.metrics["patterns_stored"] += 1

        return pattern.id

    async def get_matching_patterns(self, pattern_type: str, context: Dict, threshold: float = 0.5) -> List[Pattern]:
        """Get patterns matching the given type and context

        Args:
            pattern_type: Type of pattern to match
            context: Context to match against
            threshold: Minimum confidence threshold

        Returns:
            List[Pattern]: Matching patterns
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Get patterns of matching type
        c.execute('''
        SELECT * FROM patterns
        WHERE type = ? AND confidence >= ?
        ''', (pattern_type, threshold))

        matches = []
        for row in c.fetchall():
            # Decrypt data
            content = json.loads(self.cipher.decrypt(row[2]))
            stored_context = json.loads(self.cipher.decrypt(row[3]))

            # Check context match
            if self._context_matches(stored_context, context):
                pattern = Pattern(
                    id=row[0],
                    type=row[1],
                    content=content,
                    context=stored_context,
                    confidence=row[4],
                    created_at=datetime.fromisoformat(row[5]),
                    updated_at=datetime.fromisoformat(row[6]),
                    usage_count=row[7],
                    impact_score=row[8]
                )
                matches.append(pattern)

        conn.close()
        return matches

    async def track_pattern_evolution(self, pattern_id: str, impact: float):
        """Track pattern evolution and update metrics

        Args:
            pattern_id: Pattern ID
            impact: Impact score of pattern usage
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Update pattern metrics
        c.execute('''
        UPDATE patterns
        SET usage_count = usage_count + 1,
            impact_score = (impact_score * usage_count + ?) / (usage_count + 1),
            updated_at = ?
        WHERE id = ?
        ''', (impact, datetime.now(), pattern_id))

        # Record evolution event
        c.execute('''
        INSERT INTO evolution_events
        VALUES (?, ?, ?, ?, ?)
        ''', (
            self._generate_id(),
            pattern_id,
            "usage",
            json.dumps({"impact": impact}),
            datetime.now()
        ))

        conn.commit()
        conn.close()

        self.metrics["patterns_evolved"] += 1

    async def store_component_state(self, component: str, state: Dict):
        """Store component state

        Args:
            component: Component identifier
            state: Component state
        """
        # Encrypt state data
        encrypted_state = self.cipher.encrypt(json.dumps(state).encode())

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
        INSERT OR REPLACE INTO states
        VALUES (?, ?, ?, ?)
        ''', (
            self._generate_id(),
            component,
            encrypted_state,
            datetime.now()
        ))

        conn.commit()
        conn.close()

        # Update cache
        self.state_cache[component] = state

    async def get_component_state(self, component: str) -> Optional[Dict]:
        """Get component state

        Args:
            component: Component identifier

        Returns:
            Optional[Dict]: Component state if found
        """
        # Check cache first
        if component in self.state_cache:
            self.metrics["cache_hits"] += 1
            return self.state_cache[component]

        self.metrics["cache_misses"] += 1

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
        SELECT state FROM states
        WHERE component = ?
        ORDER BY timestamp DESC
        LIMIT 1
        ''', (component,))

        row = c.fetchone()
        conn.close()

        if row:
            state = json.loads(self.cipher.decrypt(row[0]))
            self.state_cache[component] = state
            return state

        return None

    def _generate_id(self) -> str:
        """Generate a unique ID"""
        return f"{datetime.now().timestamp()}-{np.random.randint(10000)}"

    def _context_matches(self, stored_context: Dict, query_context: Dict, threshold: float = 0.8) -> bool:
        """Check if contexts match within threshold

        Args:
            stored_context: Stored context
            query_context: Query context
            threshold: Match threshold

        Returns:
            bool: True if contexts match
        """
        # Simple matching for now - can be enhanced with more sophisticated matching
        matches = 0
        total = len(query_context)

        for key, value in query_context.items():
            if key in stored_context and stored_context[key] == value:
                matches += 1

        return (matches / total) >= threshold
