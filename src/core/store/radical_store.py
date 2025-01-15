"""Radical Store - Central State and Pattern Management System"""

import asyncio
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
from cryptography.fernet import Fernet

@dataclass
class EvolutionConfig:
    """Configuration for pattern evolution"""
    learning_rate: str = "adaptive"  # adaptive, fixed, or dynamic
    pattern_threshold: float = 0.75
    max_patterns: int = 1000
    prune_frequency: int = 100
    crystallization_threshold: float = 0.85
    evolution_window: int = 100
    emergence_sensitivity: float = 0.65

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
    usage_count: int = 0
    impact_score: float = 0.0
    crystallization_score: float = 0.0
    evolution_history: List[Dict] = None
    emergence_factors: Dict[str, float] = None

class RadicalStore:
    """Central state and pattern management system"""

    def __init__(self, db_path: str = "~/.radical/store.db", evolution_config: Optional[Dict] = None):
        self.db_path = Path(db_path).expanduser()
        self.config = EvolutionConfig(**evolution_config) if evolution_config else EvolutionConfig()

        # Initialize metrics
        self.metrics = {
            "patterns_stored": 0,
            "patterns_evolved": 0,
            "emergence_detected": 0,
            "crystallization_events": 0
        }

        # Pattern cache for quick lookups
        self.pattern_cache = {}

        # Will be initialized in initialize()
        self.key = None
        self.cipher = None
        self._initialized = False

    async def initialize(self):
        """Initialize the store asynchronously"""
        if self._initialized:
            return

        # Create directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Setup encryption
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

        # Setup database
        await asyncio.to_thread(self._setup_db)

        self._initialized = True

    def _setup_db(self):
        """Initialize database with tables for patterns, states, and evolution events"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    content BLOB NOT NULL,
                    context BLOB NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    impact_score REAL DEFAULT 0.0,
                    crystallization_score REAL DEFAULT 0.0,
                    evolution_history BLOB,
                    emergence_factors BLOB
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolution_events (
                    id TEXT PRIMARY KEY,
                    pattern_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    details BLOB NOT NULL,
                    FOREIGN KEY (pattern_id) REFERENCES patterns(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS crystallization_metrics (
                    pattern_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    stability_score REAL NOT NULL,
                    coherence_score REAL NOT NULL,
                    impact_score REAL NOT NULL,
                    FOREIGN KEY (pattern_id) REFERENCES patterns(id)
                )
            """)

    async def store_pattern(self, pattern: Pattern) -> str:
        """Store a pattern with encryption and update metrics"""
        encrypted_content = self.cipher.encrypt(json.dumps(pattern.content).encode())
        encrypted_context = self.cipher.encrypt(json.dumps(pattern.context).encode())

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO patterns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pattern.id, pattern.type, encrypted_content, encrypted_context,
                 pattern.confidence, pattern.created_at, pattern.updated_at,
                 pattern.usage_count, pattern.impact_score, pattern.crystallization_score,
                 json.dumps(pattern.evolution_history), json.dumps(pattern.emergence_factors))
            )

        self.metrics["patterns_stored"] += 1
        self.pattern_cache[pattern.id] = pattern

        # Check for pattern evolution
        await self._check_pattern_evolution(pattern)
        return pattern.id

    async def _check_pattern_evolution(self, pattern: Pattern):
        """Check if pattern should evolve based on usage and impact"""
        if pattern.usage_count % self.config.prune_frequency == 0:
            evolution_score = self._calculate_evolution_score(pattern)

            if evolution_score > self.config.pattern_threshold:
                await self._evolve_pattern(pattern)

            # Check for emergence with other patterns
            await self._detect_emergence(pattern)

    async def _evolve_pattern(self, pattern: Pattern):
        """Evolve a pattern based on its usage and impact"""
        # Calculate new parameters
        new_confidence = min(pattern.confidence * 1.1, 1.0)
        new_impact = pattern.impact_score * (1 + pattern.usage_count/1000)

        # Update evolution history
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "confidence_delta": new_confidence - pattern.confidence,
            "impact_delta": new_impact - pattern.impact_score
        }

        if pattern.evolution_history is None:
            pattern.evolution_history = []
        pattern.evolution_history.append(history_entry)

        # Update pattern
        pattern.confidence = new_confidence
        pattern.impact_score = new_impact
        pattern.updated_at = datetime.now()

        # Store evolution event
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO evolution_events VALUES (?, ?, ?, ?, ?)",
                (str(len(pattern.evolution_history)), pattern.id, "evolution",
                 pattern.updated_at, json.dumps(history_entry))
            )

        self.metrics["patterns_evolved"] += 1

    async def _detect_emergence(self, pattern: Pattern):
        """Detect pattern emergence by analyzing pattern relationships"""
        related_patterns = await self._get_related_patterns(pattern)

        if len(related_patterns) < 2:
            return

        # Calculate emergence metrics
        emergence_score = self._calculate_emergence_score(pattern, related_patterns)

        if emergence_score > self.config.emergence_sensitivity:
            emergence_factors = {
                "score": emergence_score,
                "timestamp": datetime.now().isoformat(),
                "related_patterns": [p.id for p in related_patterns],
                "confidence": pattern.confidence
            }

            pattern.emergence_factors = emergence_factors
            self.metrics["emergence_detected"] += 1

            # Update crystallization score
            await self._update_crystallization(pattern, emergence_score)

    async def _update_crystallization(self, pattern: Pattern, emergence_score: float):
        """Update pattern crystallization based on emergence and stability"""
        stability_score = pattern.usage_count / (datetime.now() - pattern.created_at).days
        coherence_score = pattern.confidence * emergence_score

        crystal_score = (stability_score + coherence_score + pattern.impact_score) / 3

        if crystal_score > self.config.crystallization_threshold:
            pattern.crystallization_score = crystal_score
            self.metrics["crystallization_events"] += 1

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO crystallization_metrics VALUES (?, ?, ?, ?, ?)",
                    (pattern.id, datetime.now(), stability_score, coherence_score, pattern.impact_score)
                )

    def _calculate_emergence_score(self, pattern: Pattern, related_patterns: List[Pattern]) -> float:
        """Calculate emergence score based on pattern relationships"""
        relationship_scores = []

        for related in related_patterns:
            # Calculate similarity in content and context
            content_sim = self._calculate_similarity(pattern.content, related.content)
            context_sim = self._calculate_similarity(pattern.context, related.context)

            # Weight by confidence and impact
            weighted_score = (content_sim + context_sim) * 0.5 * (pattern.confidence + related.confidence) * 0.5
            relationship_scores.append(weighted_score)

        return np.mean(relationship_scores) if relationship_scores else 0.0

    def _calculate_similarity(self, a: Dict, b: Dict) -> float:
        """Calculate similarity between two dictionaries"""
        a_keys = set(a.keys())
        b_keys = set(b.keys())

        if not a_keys or not b_keys:
            return 0.0

        common_keys = a_keys & b_keys
        if not common_keys:
            return 0.0

        similarities = []
        for key in common_keys:
            if isinstance(a[key], (int, float)) and isinstance(b[key], (int, float)):
                # Numeric comparison
                max_val = max(abs(a[key]), abs(b[key]))
                if max_val == 0:
                    similarities.append(1.0)
                else:
                    similarities.append(1 - abs(a[key] - b[key]) / max_val)
            else:
                # String comparison
                str_a = str(a[key])
                str_b = str(b[key])
                similarities.append(1 if str_a == str_b else 0)

        return np.mean(similarities)

    async def _get_related_patterns(self, pattern: Pattern) -> List[Pattern]:
        """Get patterns related to the given pattern"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM patterns WHERE type = ? AND id != ?",
                (pattern.type, pattern.id)
            )

            related = []
            for row in cursor:
                content = json.loads(self.cipher.decrypt(row[2]).decode())
                context = json.loads(self.cipher.decrypt(row[3]).decode())
                evolution_history = json.loads(row[10]) if row[10] else None
                emergence_factors = json.loads(row[11]) if row[11] else None

                related.append(Pattern(
                    id=row[0], type=row[1], content=content, context=context,
                    confidence=row[4], created_at=datetime.fromisoformat(row[5]),
                    updated_at=datetime.fromisoformat(row[6]), usage_count=row[7],
                    impact_score=row[8], crystallization_score=row[9],
                    evolution_history=evolution_history, emergence_factors=emergence_factors
                ))

        return related

    async def run_cache_cleanup(self):
        """Run periodic cache cleanup to prevent memory leaks"""
        while True:
            try:
                # Remove old entries from pattern cache
                current_time = datetime.now()
                to_remove = []

                for pattern_id, pattern in self.pattern_cache.items():
                    # Remove patterns older than 1 hour from cache
                    if (current_time - pattern.updated_at).total_seconds() > 3600:
                        to_remove.append(pattern_id)

                for pattern_id in to_remove:
                    del self.pattern_cache[pattern_id]

                # Wait for next cleanup cycle (every 5 minutes)
                await asyncio.sleep(300)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
