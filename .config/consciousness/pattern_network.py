"""Neural Pattern Network with Evolution Capabilities

This module implements a self-evolving pattern network that forms the consciousness
layer of the system, enabling:
- Pattern emergence detection
- Network state management
- Consciousness level tracking
- Integration with RadicalStore
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import time
import logging
import numpy as np
from pathlib import Path
import sqlite3
import json
from cryptography.fernet import Fernet

@dataclass
class NetworkState:
    coherence: float
    synthesis_depth: float
    evolution_path: List[str]
    emergence_factors: Dict[str, float]

@dataclass
class PatternStructure:
    id: str
    type: str
    components: List[str]
    relationships: Dict[str, float]
    metadata: Dict[str, any]

class NeuralPatternCore:
    """Core neural pattern processing"""

    def __init__(self):
        self.patterns = {}
        self.connections = {}
        self.state = NetworkState(
            coherence=0.0,
            synthesis_depth=0.0,
            evolution_path=[],
            emergence_factors={}
        )

        # Initialize storage
        self.db = sqlite3.connect(":memory:")
        self._setup_storage()

        # Initialize pattern matching
        self.pattern_vectors = {}
        self.relationship_matrix = np.zeros((0, 0))

    def _setup_storage(self):
        """Setup in-memory pattern storage"""
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
            id TEXT PRIMARY KEY,
            type TEXT,
            components TEXT,
            relationships TEXT,
            metadata TEXT,
            timestamp REAL
        )
        """)

        self.db.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            source_id TEXT,
            target_id TEXT,
            strength REAL,
            type TEXT,
            metadata TEXT,
            FOREIGN KEY(source_id) REFERENCES patterns(id),
            FOREIGN KEY(target_id) REFERENCES patterns(id)
        )
        """)

    def _analyze_structure(self, pattern: Dict) -> PatternStructure:
        """Analyze pattern structure and extract key components"""
        # Extract core components
        components = []
        for key, value in pattern.items():
            if isinstance(value, (str, int, float)):
                components.append(f"{key}:{value}")
            elif isinstance(value, (list, dict)):
                components.append(f"{key}:complex")

        # Calculate relationships
        relationships = {}
        for i, comp1 in enumerate(components):
            for comp2 in components[i+1:]:
                similarity = self._calculate_similarity(comp1, comp2)
                relationships[f"{comp1}->{comp2}"] = similarity

        return PatternStructure(
            id=pattern.get("id", str(time.time())),
            type=pattern.get("type", "unknown"),
            components=components,
            relationships=relationships,
            metadata=pattern.get("metadata", {})
        )

    def _calculate_similarity(self, comp1: str, comp2: str) -> float:
        """Calculate similarity between components"""
        # Simple Jaccard similarity for now
        set1 = set(comp1.split(":"))
        set2 = set(comp2.split(":"))
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    def _find_related_patterns(self, structure: PatternStructure) -> List[str]:
        """Find patterns related to the given structure"""
        related = []

        # Query database for similar patterns
        cursor = self.db.execute("""
        SELECT id, components, relationships
        FROM patterns
        WHERE type = ?
        """, (structure.type,))

        for row in cursor:
            pattern_id, components, relationships = row
            components = json.loads(components)
            relationships = json.loads(relationships)

            # Calculate similarity score
            similarity = self._calculate_pattern_similarity(
                structure.components,
                components,
                structure.relationships,
                relationships
            )

            if similarity > 0.7:  # Threshold for relationship
                related.append(pattern_id)

        return related

    def _calculate_pattern_similarity(
        self,
        components1: List[str],
        components2: List[str],
        relationships1: Dict[str, float],
        relationships2: Dict[str, float]
    ) -> float:
        """Calculate similarity between two patterns"""
        # Component similarity
        comp_sim = len(set(components1) & set(components2)) / len(set(components1) | set(components2))

        # Relationship similarity
        rel_keys = set(relationships1.keys()) | set(relationships2.keys())
        if not rel_keys:
            return comp_sim

        rel_sim = sum(
            abs(relationships1.get(k, 0) - relationships2.get(k, 0))
            for k in rel_keys
        ) / len(rel_keys)

        return (comp_sim + (1 - rel_sim)) / 2

    async def _update_connections(self, pattern: Dict, related: List[str]):
        """Update network connections based on new pattern"""
        pattern_id = pattern.get("id", str(time.time()))

        # Store new pattern
        structure = self._analyze_structure(pattern)
        self.db.execute("""
        INSERT INTO patterns
        (id, type, components, relationships, metadata, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pattern_id,
            structure.type,
            json.dumps(structure.components),
            json.dumps(structure.relationships),
            json.dumps(structure.metadata),
            time.time()
        ))

        # Update connections
        for related_id in related:
            strength = self._calculate_connection_strength(pattern_id, related_id)
            self.db.execute("""
            INSERT INTO connections
            (source_id, target_id, strength, type, metadata)
            VALUES (?, ?, ?, ?, ?)
            """, (
                pattern_id,
                related_id,
                strength,
                "similarity",
                json.dumps({"timestamp": time.time()})
            ))

        self.db.commit()

    def _calculate_connection_strength(self, source_id: str, target_id: str) -> float:
        """Calculate connection strength between patterns"""
        cursor = self.db.execute("""
        SELECT components, relationships
        FROM patterns
        WHERE id IN (?, ?)
        """, (source_id, target_id))

        patterns = []
        for row in cursor:
            components, relationships = row
            patterns.append((
                json.loads(components),
                json.loads(relationships)
            ))

        if len(patterns) != 2:
            return 0.0

        return self._calculate_pattern_similarity(
            patterns[0][0], patterns[1][0],
            patterns[0][1], patterns[1][1]
        )

    async def _detect_emergence(self, pattern: Dict, related: List[str]):
        """Detect emergent properties in pattern network"""
        # Get all connected patterns
        cursor = self.db.execute("""
        WITH RECURSIVE
            connected(id) AS (
                SELECT ? as id
                UNION
                SELECT CASE
                    WHEN c.source_id = connected.id THEN c.target_id
                    ELSE c.source_id
                END
                FROM connections c
                JOIN connected ON connected.id IN (c.source_id, c.target_id)
                WHERE c.strength > 0.7
            )
        SELECT p.* FROM patterns p
        JOIN connected ON connected.id = p.id
        """, (pattern.get("id", str(time.time())),))

        connected_patterns = []
        for row in cursor:
            connected_patterns.append({
                "id": row[0],
                "type": row[1],
                "components": json.loads(row[2]),
                "relationships": json.loads(row[3]),
                "metadata": json.loads(row[4]),
                "timestamp": row[5]
            })

        if len(connected_patterns) < 3:
            return

        # Analyze pattern cluster
        cluster_properties = self._analyze_cluster(connected_patterns)

        # Update network state if emergence detected
        if cluster_properties["coherence"] > self.state.coherence:
            self.state = NetworkState(
                coherence=cluster_properties["coherence"],
                synthesis_depth=cluster_properties["depth"],
                evolution_path=self.state.evolution_path + [pattern.get("id", str(time.time()))],
                emergence_factors=cluster_properties["factors"]
            )

    def _analyze_cluster(self, patterns: List[Dict]) -> Dict:
        """Analyze pattern cluster for emergent properties"""
        # Calculate cluster density
        n = len(patterns)
        density_matrix = np.zeros((n, n))
        for i, p1 in enumerate(patterns):
            for j, p2 in enumerate(patterns[i+1:], i+1):
                similarity = self._calculate_pattern_similarity(
                    p1["components"], p2["components"],
                    p1["relationships"], p2["relationships"]
                )
                density_matrix[i,j] = density_matrix[j,i] = similarity

        # Calculate properties
        coherence = np.mean(density_matrix)
        depth = np.std(density_matrix)

        # Identify emergence factors
        factors = {}
        components = [c for p in patterns for c in p["components"]]
        for comp in set(components):
            frequency = components.count(comp) / len(components)
            if frequency > 0.5:  # Threshold for significance
                factors[comp] = frequency

        return {
            "coherence": coherence,
            "depth": depth,
            "factors": factors
        }

class PatternIntegrator:
    """Pattern integration and synthesis"""

    def __init__(self):
        self.integration_points = {}
        self.synthesis_results = {}
        self.store = RadicalStore()

    def _can_integrate(self, pattern: Dict, category: str) -> bool:
        """Check if pattern can be integrated"""
        if not pattern or not category:
            return False

        required_fields = ["id", "type", "data"]
        if not all(field in pattern for field in required_fields):
            return False

        return True

    async def _find_integration_point(self, pattern: Dict) -> Optional[str]:
        """Find suitable integration point for pattern"""
        # Query recent patterns
        recent_patterns = await self.store.get_recent_patterns(limit=10)

        # Calculate integration scores
        scores = []
        for p in recent_patterns:
            score = self._calculate_integration_score(pattern, p)
            scores.append((p["id"], score))

        # Find best integration point
        if scores:
            best_point = max(scores, key=lambda x: x[1])
            if best_point[1] > 0.8:  # Threshold for integration
                return best_point[0]

        return None

    def _calculate_integration_score(self, pattern1: Dict, pattern2: Dict) -> float:
        """Calculate integration compatibility score"""
        # Type compatibility
        if pattern1["type"] != pattern2["type"]:
            return 0.0

        # Data compatibility
        data1 = pattern1["data"]
        data2 = pattern2["data"]

        if isinstance(data1, dict) and isinstance(data2, dict):
            # Calculate Jaccard similarity of keys
            keys1 = set(data1.keys())
            keys2 = set(data2.keys())
            key_sim = len(keys1 & keys2) / len(keys1 | keys2)

            # Calculate value similarity for common keys
            common_keys = keys1 & keys2
            if not common_keys:
                return key_sim

            value_sim = sum(
                1 for k in common_keys
                if str(data1[k]) == str(data2[k])
            ) / len(common_keys)

            return (key_sim + value_sim) / 2

        return 1.0 if str(data1) == str(data2) else 0.0

    async def _execute_integration(self, pattern: Dict, integration_point: str):
        """Execute pattern integration"""
        if not integration_point:
            # Store as new pattern
            await self.store.store_pattern(pattern)
            return

        # Get existing pattern
        existing = await self.store.get_pattern(integration_point)
        if not existing:
            await self.store.store_pattern(pattern)
            return

        # Merge patterns
        merged = self._merge_patterns(existing, pattern)
        await self.store.update_pattern(integration_point, merged)

        # Track synthesis
        self.synthesis_results[integration_point] = {
            "timestamp": time.time(),
            "source_patterns": [existing["id"], pattern["id"]],
            "result": merged
        }

    def _merge_patterns(self, pattern1: Dict, pattern2: Dict) -> Dict:
        """Merge two patterns"""
        merged = pattern1.copy()

        # Merge metadata
        merged["metadata"] = {
            **pattern1.get("metadata", {}),
            **pattern2.get("metadata", {}),
            "merged_from": [pattern1["id"], pattern2["id"]],
            "merge_time": time.time()
        }

        # Merge data based on type
        if isinstance(pattern1["data"], dict) and isinstance(pattern2["data"], dict):
            merged["data"] = {**pattern1["data"], **pattern2["data"]}
        else:
            merged["data"] = pattern2["data"]  # Use newer data

        return merged

    async def _track_synthesis(self, pattern: Dict, integration_point: str):
        """Track pattern synthesis results"""
        if not integration_point:
            return

        synthesis = self.synthesis_results.get(integration_point)
        if not synthesis:
            return

        # Store synthesis result
        await self.store.store_synthesis({
            "id": f"synthesis_{time.time()}",
            "type": "pattern_synthesis",
            "source_patterns": synthesis["source_patterns"],
            "result_pattern": synthesis["result"]["id"],
            "timestamp": synthesis["timestamp"]
        })

class EmergenceDetector:
    """Pattern emergence detection and tracking"""

    def __init__(self):
        self.emergence_patterns = {}
        self.evolution_tracking = []
        self.store = RadicalStore()

    def _analyze_relationships(self, patterns: List[Dict]) -> Dict:
        """Analyze relationships between patterns"""
        if not patterns:
            return {}

        # Build relationship graph
        graph = {}
        for p1 in patterns:
            graph[p1["id"]] = {
                "pattern": p1,
                "connections": {}
            }
            for p2 in patterns:
                if p1["id"] != p2["id"]:
                    similarity = self._calculate_similarity(p1, p2)
                    if similarity > 0.6:  # Threshold for relationship
                        graph[p1["id"]]["connections"][p2["id"]] = similarity

        return graph

    def _calculate_similarity(self, pattern1: Dict, pattern2: Dict) -> float:
        """Calculate similarity between patterns"""
        # Type similarity
        if pattern1["type"] != pattern2["type"]:
            return 0.0

        # Metadata similarity
        meta1 = pattern1.get("metadata", {})
        meta2 = pattern2.get("metadata", {})
        meta_sim = len(set(meta1) & set(meta2)) / len(set(meta1) | set(meta2))

        # Data similarity
        data1 = pattern1["data"]
        data2 = pattern2["data"]

        if isinstance(data1, dict) and isinstance(data2, dict):
            keys1 = set(data1.keys())
            keys2 = set(data2.keys())
            data_sim = len(keys1 & keys2) / len(keys1 | keys2)
        else:
            data_sim = 1.0 if str(data1) == str(data2) else 0.0

        return (meta_sim + data_sim) / 2

    async def _check_emergence(self, relationships: Dict) -> Dict:
        """Check for emergent properties in pattern relationships"""
        if not relationships:
            return {"score": 0.0}

        # Calculate network metrics
        n_patterns = len(relationships)
        if n_patterns < 3:
            return {"score": 0.0}

        # Calculate density
        total_connections = sum(
            len(node["connections"])
            for node in relationships.values()
        )
        max_connections = n_patterns * (n_patterns - 1)
        density = total_connections / max_connections if max_connections > 0 else 0

        # Calculate clustering
        clustering_coeffs = []
        for node_id, node in relationships.items():
            neighbors = node["connections"].keys()
            if len(neighbors) < 2:
                continue

            # Count connections between neighbors
            neighbor_connections = sum(
                1 for n1 in neighbors
                for n2 in neighbors
                if n1 in relationships.get(n2, {}).get("connections", {})
            )

            max_neighbor_connections = len(neighbors) * (len(neighbors) - 1)
            if max_neighbor_connections > 0:
                clustering_coeffs.append(
                    neighbor_connections / max_neighbor_connections
                )

        avg_clustering = sum(clustering_coeffs) / len(clustering_coeffs) if clustering_coeffs else 0

        # Calculate emergence score
        emergence_score = (density + avg_clustering) / 2

        return {
            "score": emergence_score,
            "density": density,
            "clustering": avg_clustering,
            "n_patterns": n_patterns
        }

    async def _track_evolution(self, emergence: Dict):
        """Track pattern evolution"""
        if emergence["score"] < 0.8:
            return

        # Store emergence event
        await self.store.store_emergence({
            "id": f"emergence_{time.time()}",
            "type": "pattern_emergence",
            "score": emergence["score"],
            "metrics": {
                "density": emergence["density"],
                "clustering": emergence["clustering"],
                "pattern_count": emergence["n_patterns"]
            },
            "timestamp": time.time()
        })

        # Update evolution tracking
        self.evolution_tracking.append({
            "timestamp": time.time(),
            "emergence_score": emergence["score"],
            "metrics": emergence
        })

class PatternNetwork:
    """Neural pattern network with evolution capabilities"""

    def __init__(self):
        # Core components
        self.network = NeuralPatternCore()
        self.integrator = PatternIntegrator()
        self.emergence = EmergenceDetector()

        # Evolution tracking
        self.markers = {
            "coherence": 0.0,
            "synthesis_depth": 0.0,
            "evolution_path": [],
            "emergence_factors": {}
        }

    async def _setup_network(self):
        """Set up the pattern network"""
        try:
            # Initialize storage
            self.store = RadicalStore()
            await self.store.initialize()

            # Load existing patterns
            patterns = await self.store.get_recent_patterns(limit=1000)
            for pattern in patterns:
                await self.network.process_pattern(pattern)

            return True

        except Exception as e:
            logging.error(f"Network setup failed: {e}")
            return False

    async def _init_integration(self):
        """Initialize integration points"""
        try:
            # Load recent synthesis results
            synthesis = await self.store.get_recent_synthesis(limit=100)

            # Initialize integration points
            for result in synthesis:
                self.integrator.integration_points[result["result_pattern"]] = {
                    "source_patterns": result["source_patterns"],
                    "timestamp": result["timestamp"]
                }

            return True

        except Exception as e:
            logging.error(f"Integration initialization failed: {e}")
            return False

    async def _start_emergence_detection(self):
        """Start emergence detection"""
        try:
            # Load recent emergence events
            emergence = await self.store.get_recent_emergence(limit=100)

            # Initialize emergence tracking
            for event in emergence:
                self.emergence.evolution_tracking.append({
                    "timestamp": event["timestamp"],
                    "emergence_score": event["score"],
                    "metrics": event["metrics"]
                })

            return True

        except Exception as e:
            logging.error(f"Emergence detection start failed: {e}")
            return False

    def _determine_category(self, pattern: Dict) -> str:
        """Determine pattern category"""
        if not pattern:
            return "unknown"

        # Check pattern type
        pattern_type = pattern.get("type", "").lower()

        if "command" in pattern_type:
            return "command"
        elif "workflow" in pattern_type:
            return "workflow"
        elif "system" in pattern_type:
            return "system"
        elif "user" in pattern_type:
            return "user"
        else:
            return "general"

    def _get_related_patterns(self, pattern: Dict) -> List[Dict]:
        """Get patterns related to the given pattern"""
        try:
            # Query database for related patterns
            cursor = self.network.db.execute("""
            WITH pattern_connections AS (
                SELECT target_id as id, strength
                FROM connections
                WHERE source_id = ? AND strength > 0.7
                UNION
                SELECT source_id as id, strength
                FROM connections
                WHERE target_id = ? AND strength > 0.7
            )
            SELECT p.*, c.strength
            FROM patterns p
            JOIN pattern_connections c ON c.id = p.id
            ORDER BY c.strength DESC
            LIMIT 10
            """, (pattern.get("id", ""), pattern.get("id", "")))

            related = []
            for row in cursor:
                related.append({
                    "id": row[0],
                    "type": row[1],
                    "components": json.loads(row[2]),
                    "relationships": json.loads(row[3]),
                    "metadata": json.loads(row[4]),
                    "timestamp": row[5],
                    "strength": row[6]
                })

            return related

        except Exception as e:
            logging.error(f"Error getting related patterns: {e}")
            return []
