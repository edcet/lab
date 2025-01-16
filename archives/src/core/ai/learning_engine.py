from typing import Dict, List, Any, Optional
import numpy as np
from datetime import datetime
from .pattern_recognition import PatternEngine, Pattern

class ActionResult:
    """Tracks the result of an action for learning"""
    def __init__(self, success: bool, impact: float, execution_time: float):
        self.success = success
        self.impact = impact
        self.execution_time = execution_time
        self.timestamp = datetime.now()

class LearningEngine:
    """Core learning engine with pattern-based decision making"""

    def __init__(self):
        self.pattern_engine = PatternEngine()
        self.action_history: List[Dict] = []
        self.success_threshold = 0.7
        self.min_confidence = 0.8

    async def process(self, state: Dict) -> Dict[str, Any]:
        """Process current state and return action decision"""
        # Analyze patterns in current state
        analysis = self.pattern_engine.analyze(state)

        if not analysis["matches"]:
            # No matching patterns - use exploration
            return self._explore_action(state)

        # Get best matching pattern
        best_match = analysis["matches"][0]

        if best_match["success_rate"] >= self.success_threshold and \
           best_match["similarity"] >= self.min_confidence:
            # Use pattern-based action
            return self._exploit_pattern(best_match, state)
        else:
            # Explore new action
            return self._explore_action(state)

    def learn(self, state: Dict, action: Dict, result: ActionResult):
        """Learn from action result"""
        # Record action result
        self.action_history.append({
            "state": state,
            "action": action,
            "result": {
                "success": result.success,
                "impact": result.impact,
                "execution_time": result.execution_time,
                "timestamp": result.timestamp
            }
        })

        # Learn pattern
        self.pattern_engine.learn_pattern(
            data={**state, **action},
            success=result.success,
            impact=result.impact
        )

        # Prune patterns if needed
        self.pattern_engine.prune_patterns()

    def _explore_action(self, state: Dict) -> Dict[str, Any]:
        """Generate exploratory action"""
        return {
            "type": "explore",
            "confidence": 0.5,
            "action": self._generate_action(state)
        }

    def _exploit_pattern(self, pattern_match: Dict, state: Dict) -> Dict[str, Any]:
        """Generate action based on pattern"""
        return {
            "type": "exploit",
            "confidence": pattern_match["similarity"],
            "action": self._generate_action(state, pattern_match)
        }

    def _generate_action(self, state: Dict, pattern_match: Optional[Dict] = None) -> Dict:
        """Generate concrete action based on state and optional pattern"""
        if pattern_match:
            # Use pattern to influence action generation
            return {
                "name": "pattern_based_action",
                "params": {
                    "confidence": pattern_match["similarity"],
                    "success_rate": pattern_match["success_rate"],
                    "impact_score": pattern_match["impact_score"]
                }
            }
        else:
            # Generate exploratory action
            return {
                "name": "exploratory_action",
                "params": {
                    "state_size": len(self._extract_features(state)),
                    "timestamp": datetime.now().isoformat()
                }
            }

    def _extract_features(self, state: Dict) -> List[float]:
        """Extract relevant features from state"""
        features = []

        # Extract numerical values
        def extract_numbers(obj):
            if isinstance(obj, (int, float)):
                features.append(float(obj))
            elif isinstance(obj, dict):
                for v in obj.values():
                    extract_numbers(v)
            elif isinstance(obj, (list, tuple)):
                for v in obj:
                    extract_numbers(v)

        extract_numbers(state)
        return features

    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics"""
        if not self.action_history:
            return {
                "total_actions": 0,
                "success_rate": 0.0,
                "avg_impact": 0.0,
                "patterns": 0
            }

        recent_actions = self.action_history[-100:]  # Look at last 100 actions

        return {
            "total_actions": len(self.action_history),
            "success_rate": np.mean([a["result"]["success"] for a in recent_actions]),
            "avg_impact": np.mean([a["result"]["impact"] for a in recent_actions]),
            "avg_execution_time": np.mean([a["result"]["execution_time"] for a in recent_actions]),
            "patterns": len(self.pattern_engine.patterns),
            "top_patterns": [
                {
                    "id": p.id,
                    "success_rate": p.success_rate,
                    "impact_score": p.impact_score,
                    "frequency": p.frequency
                }
                for p in self.pattern_engine.get_top_patterns(3)
            ]
        }
