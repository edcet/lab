from typing import Dict, Any, Set, Optional, List
import sqlite3
import hashlib
import time
import asyncio
import logging
from collections import deque
import numpy as np
from dataclasses import dataclass
from datetime import datetime

from .pattern_recognition import PatternEngine, Pattern

@dataclass
class StreamPattern:
    """Pattern extracted from data stream"""
    id: str
    data: bytes
    features: np.ndarray
    timestamp: float
    frequency: int = 1

class DeepInterceptor:
    """Core stream interception"""

    def __init__(self, ports: List[int]):
        self.ports = ports
        self.active_ports = set()
        self.buffer_size = 8192

    async def capture(self, data: bytes) -> bytes:
        """Capture and preprocess stream data"""
        # Basic preprocessing only - no fluff
        if len(data) > self.buffer_size:
            data = data[:self.buffer_size]
        return data

class PatternMiner:
    """Extract patterns from data streams"""

    def __init__(self):
        self.pattern_engine = PatternEngine(feature_dim=256)  # Larger feature space for streams
        self.min_pattern_len = 16
        self.max_patterns = 100

    async def analyze(self, data: bytes) -> List[StreamPattern]:
        """Extract patterns from binary data"""
        patterns = []

        # Split data into chunks
        chunks = self._chunk_data(data)

        # Extract features from each chunk
        for chunk in chunks:
            if len(chunk) < self.min_pattern_len:
                continue

            # Get numerical features
            features = self._extract_features(chunk)

            # Find similar patterns
            similar = self.pattern_engine.find_similar_patterns(features)

            if similar:
                # Update existing pattern
                pattern_id = similar[0][0]
                pattern = StreamPattern(
                    id=pattern_id,
                    data=chunk,
                    features=features,
                    timestamp=time.time()
                )
            else:
                # New pattern
                pattern = StreamPattern(
                    id=hashlib.sha256(chunk).hexdigest()[:16],
                    data=chunk,
                    features=features,
                    timestamp=time.time()
                )

            patterns.append(pattern)

            if len(patterns) >= self.max_patterns:
                break

        return patterns

    def _chunk_data(self, data: bytes, chunk_size: int = 64) -> List[bytes]:
        """Split data into overlapping chunks"""
        chunks = []
        for i in range(0, len(data) - chunk_size + 1, chunk_size // 2):
            chunks.append(data[i:i + chunk_size])
        return chunks

    def _extract_features(self, data: bytes) -> np.ndarray:
        """Extract numerical features from binary data"""
        # Convert to numerical array
        values = np.frombuffer(data, dtype=np.uint8)

        # Extract statistical features
        features = [
            np.mean(values),
            np.std(values),
            np.median(values),
            *np.percentile(values, [25, 75]),
            np.max(values),
            np.min(values),
            len(set(values)) / len(values)  # Entropy approximation
        ]

        # Normalize
        features = np.array(features, dtype=np.float32)
        features = features / (np.linalg.norm(features) + 1e-8)

        return features

class LocalVault:
    """Secure pattern storage"""

    def __init__(self, path: str):
        self.path = path
        self.db = sqlite3.connect(path)
        self._setup_storage()

    def _setup_storage(self):
        """Setup pattern storage tables"""
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
            id TEXT PRIMARY KEY,
            data BLOB,
            features BLOB,
            timestamp REAL,
            frequency INTEGER
        )""")
        self.db.commit()

    async def store(self, pattern: StreamPattern):
        """Store pattern securely"""
        self.db.execute(
            "INSERT OR REPLACE INTO patterns VALUES (?, ?, ?, ?, ?)",
            (
                pattern.id,
                pattern.data,
                pattern.features.tobytes(),
                pattern.timestamp,
                pattern.frequency
            )
        )
        self.db.commit()

    async def retrieve(self, pattern_id: str) -> Optional[StreamPattern]:
        """Retrieve pattern by ID"""
        row = self.db.execute(
            "SELECT * FROM patterns WHERE id = ?",
            (pattern_id,)
        ).fetchone()

        if row:
            return StreamPattern(
                id=row[0],
                data=row[1],
                features=np.frombuffer(row[2], dtype=np.float32),
                timestamp=row[3],
                frequency=row[4]
            )
        return None

class DeepInterceptionSystem:
    """Deep packet and pattern interception system"""

    def __init__(self, config: Dict[str, Any]):
        # Core components
        self.interceptor = DeepInterceptor(config["ports"])
        self.pattern_miner = PatternMiner()
        self.vault = LocalVault(config["vault_path"])

        # Active state
        self.active_streams: Set[str] = set()
        self.pattern_buffer = deque(maxlen=1000)

        # Performance tracking
        self.stats = {
            "streams_processed": 0,
            "patterns_found": 0,
            "processing_times": deque(maxlen=100)
        }

    async def intercept(self, stream_data: bytes) -> Dict:
        """Intercept and analyze stream data"""
        try:
            start_time = time.time()

            # Get stream ID
            stream_id = hashlib.sha256(stream_data).hexdigest()[:16]
            self.active_streams.add(stream_id)

            # Capture and preprocess
            processed_data = await self.interceptor.capture(stream_data)

            # Extract patterns
            patterns = await self.pattern_miner.analyze(processed_data)

            # Store valuable patterns
            stored_patterns = []
            for pattern in patterns:
                if self._is_valuable(pattern):
                    await self.vault.store(pattern)
                    self.pattern_buffer.append(pattern)
                    stored_patterns.append(pattern.id)

            # Update stats
            duration = time.time() - start_time
            self._update_stats(len(patterns), duration)

            return {
                "stream_id": stream_id,
                "patterns": stored_patterns,
                "stats": {
                    "duration": duration,
                    "patterns_found": len(patterns),
                    "patterns_stored": len(stored_patterns)
                }
            }

        except Exception as e:
            logging.error(f"Interception error: {e}")
            return {
                "error": str(e),
                "stream_id": None,
                "patterns": []
            }

    def _is_valuable(self, pattern: StreamPattern) -> bool:
        """Determine if pattern is worth keeping"""
        # Check pattern properties
        if len(pattern.data) < self.pattern_miner.min_pattern_len:
            return False

        # Check feature properties
        feature_mean = np.mean(pattern.features)
        feature_std = np.std(pattern.features)

        return (
            feature_mean > 0.1 and  # Has significant signal
            feature_std > 0.05 and  # Has variation
            pattern.frequency < 100  # Not too common
        )

    def _update_stats(self, num_patterns: int, duration: float):
        """Update performance statistics"""
        self.stats["streams_processed"] += 1
        self.stats["patterns_found"] += num_patterns
        self.stats["processing_times"].append(duration)

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return {
            "streams_processed": self.stats["streams_processed"],
            "patterns_found": self.stats["patterns_found"],
            "avg_processing_time": np.mean(self.stats["processing_times"]),
            "active_streams": len(self.active_streams),
            "pattern_buffer_size": len(self.pattern_buffer)
        }
