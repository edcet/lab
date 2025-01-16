from typing import Dict, List, Optional, Set, Tuple
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

@dataclass
class Pattern:
    """Core pattern structure with essential metrics"""
    id: str
    features: np.ndarray
    frequency: int
    last_seen: datetime
    success_rate: float
    impact_score: float

class PatternEngine:
    """Core pattern recognition and learning engine"""

    def __init__(self, feature_dim: int = 128):
        self.patterns: Dict[str, Pattern] = {}
        self.feature_dim = feature_dim
        self.pattern_vectors = np.zeros((0, feature_dim))
        self.min_similarity = 0.85

    def extract_features(self, data: Dict) -> np.ndarray:
        """Extract numerical features from input data"""
        features = []

        # Extract numerical values
        for value in self._traverse_dict(data):
            if isinstance(value, (int, float)):
                features.append(value)

        # Normalize and pad/truncate to feature_dim
        if features:
            features = np.array(features, dtype=np.float32)
            features = features / (np.linalg.norm(features) + 1e-8)

            if len(features) > self.feature_dim:
                features = features[:self.feature_dim]
            elif len(features) < self.feature_dim:
                features = np.pad(features, (0, self.feature_dim - len(features)))

        else:
            features = np.zeros(self.feature_dim)

        return features

    def _traverse_dict(self, d: Dict) -> List:
        """Traverse dictionary and extract all values"""
        values = []
        for v in d.values():
            if isinstance(v, dict):
                values.extend(self._traverse_dict(v))
            elif isinstance(v, (list, tuple, set)):
                values.extend(self._traverse_sequence(v))
            else:
                values.append(v)
        return values

    def _traverse_sequence(self, seq) -> List:
        """Traverse sequence and extract all values"""
        values = []
        for v in seq:
            if isinstance(v, dict):
                values.extend(self._traverse_dict(v))
            elif isinstance(v, (list, tuple, set)):
                values.extend(self._traverse_sequence(v))
            else:
                values.append(v)
        return values

    def find_similar_patterns(self, features: np.ndarray, threshold: Optional[float] = None) -> List[Tuple[str, float]]:
        """Find similar patterns using cosine similarity"""
        if len(self.patterns) == 0:
            return []

        threshold = threshold or self.min_similarity
        pattern_vectors = np.array([p.features for p in self.patterns.values()])

        # Calculate cosine similarity
        similarities = np.dot(pattern_vectors, features) / (
            np.linalg.norm(pattern_vectors, axis=1) * np.linalg.norm(features) + 1e-8
        )

        # Get patterns above threshold
        similar_indices = np.where(similarities >= threshold)[0]
        similar_patterns = []

        for idx in similar_indices:
            pattern_id = list(self.patterns.keys())[idx]
            similarity = similarities[idx]
            similar_patterns.append((pattern_id, float(similarity)))

        return sorted(similar_patterns, key=lambda x: x[1], reverse=True)

    def learn_pattern(self, data: Dict, success: bool = True, impact: float = 0.0):
        """Learn new pattern or update existing one"""
        features = self.extract_features(data)
        similar = self.find_similar_patterns(features)

        if similar:
            # Update existing pattern
            pattern_id = similar[0][0]
            pattern = self.patterns[pattern_id]
            pattern.frequency += 1
            pattern.last_seen = datetime.now()

            # Update success rate with exponential moving average
            alpha = 0.1
            pattern.success_rate = (1 - alpha) * pattern.success_rate + alpha * float(success)

            # Update impact score
            pattern.impact_score = (1 - alpha) * pattern.impact_score + alpha * impact

        else:
            # Create new pattern
            pattern_id = f"pattern_{len(self.patterns)}"
            self.patterns[pattern_id] = Pattern(
                id=pattern_id,
                features=features,
                frequency=1,
                last_seen=datetime.now(),
                success_rate=float(success),
                impact_score=impact
            )

            # Update pattern vectors
            self.pattern_vectors = np.vstack([self.pattern_vectors, features])

    def get_top_patterns(self, n: int = 5) -> List[Pattern]:
        """Get top patterns by impact score"""
        return sorted(
            self.patterns.values(),
            key=lambda p: p.impact_score * p.success_rate * np.log1p(p.frequency),
            reverse=True
        )[:n]

    def prune_patterns(self, max_patterns: int = 1000):
        """Prune low-impact patterns when exceeding max_patterns"""
        if len(self.patterns) > max_patterns:
            # Sort by combined score
            patterns = self.get_top_patterns(n=max_patterns)

            # Update patterns and vectors
            self.patterns = {p.id: p for p in patterns}
            self.pattern_vectors = np.array([p.features for p in patterns])

    def analyze(self, data: Dict) -> Dict[str, Any]:
        """Analyze input data and return relevant patterns"""
        features = self.extract_features(data)
        similar = self.find_similar_patterns(features)

        if not similar:
            return {
                "matches": [],
                "recommendation": "No matching patterns found"
            }

        matches = []
        for pattern_id, similarity in similar:
            pattern = self.patterns[pattern_id]
            matches.append({
                "id": pattern.id,
                "similarity": similarity,
                "frequency": pattern.frequency,
                "success_rate": pattern.success_rate,
                "impact_score": pattern.impact_score
            })

        # Get top pattern
        top_pattern = self.patterns[similar[0][0]]

        return {
            "matches": matches,
            "recommendation": self._generate_recommendation(top_pattern)
        }

    def _generate_recommendation(self, pattern: Pattern) -> str:
        """Generate action recommendation based on pattern"""
        if pattern.success_rate > 0.8 and pattern.impact_score > 0.7:
            return "High confidence pattern - proceed with pattern-based action"
        elif pattern.success_rate > 0.6:
            return "Moderate confidence - proceed with caution"
        else:
            return "Low confidence pattern - gather more data"
