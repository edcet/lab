"""Shell Command Analyzers

This module implements specialized analyzers for shell command patterns,
workflows, and context awareness.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import re
import time

@dataclass
class AnalysisResult:
    """Analysis result with confidence and insights"""
    confidence: float
    patterns: List[Dict]
    insights: List[str]
    metadata: Dict

class BaseAnalyzer:
    """Base class for shell command analyzers"""

    def __init__(self):
        self.patterns = []
        self.history = []

    async def analyze(self, command: str, context: Dict) -> AnalysisResult:
        """Analyze command and return results"""
        raise NotImplementedError

    def _calculate_confidence(self, matches: int, total: int) -> float:
        """Calculate confidence score"""
        if total == 0:
            return 0.0
        return min(matches / total, 1.0)

class CommandAnalyzer(BaseAnalyzer):
    """Analyzes individual command patterns"""

    def __init__(self):
        super().__init__()
        # Common command patterns
        self.command_patterns = {
            "file_ops": r"(cp|mv|rm|touch|mkdir|rmdir)",
            "navigation": r"(cd|pushd|popd|pwd)",
            "search": r"(find|grep|locate|which)",
            "process": r"(ps|top|kill|pkill)",
            "network": r"(ping|curl|wget|nc|ssh)",
            "package": r"(apt|brew|pip|npm)",
            "git": r"git\s+(add|commit|push|pull|clone|checkout)"
        }

    async def analyze(self, command: str, context: Dict) -> AnalysisResult:
        """Analyze command structure and patterns"""
        patterns = []
        insights = []
        matches = 0

        # Check command against known patterns
        for category, pattern in self.command_patterns.items():
            if re.search(pattern, command):
                matches += 1
                patterns.append({
                    "category": category,
                    "pattern": pattern,
                    "command": command
                })
                insights.append(f"Command matches {category} pattern")

        # Check for pipes and redirections
        if "|" in command:
            patterns.append({
                "category": "pipeline",
                "components": command.split("|")
            })
            insights.append("Command uses pipeline processing")

        if ">" in command or ">>" in command:
            patterns.append({
                "category": "redirection",
                "command": command
            })
            insights.append("Command uses file redirection")

        # Calculate confidence
        confidence = self._calculate_confidence(matches, len(self.command_patterns))

        return AnalysisResult(
            confidence=confidence,
            patterns=patterns,
            insights=insights,
            metadata={"timestamp": time.time()}
        )

class WorkflowAnalyzer(BaseAnalyzer):
    """Analyzes command workflows and sequences"""

    def __init__(self):
        super().__init__()
        self.workflow_patterns = {
            "build": ["configure", "make", "make install"],
            "git_flow": ["git pull", "git add", "git commit", "git push"],
            "deployment": ["build", "test", "deploy"],
            "data_processing": ["download", "process", "analyze"]
        }

    async def analyze(self, command: str, context: Dict) -> AnalysisResult:
        """Analyze workflow patterns"""
        patterns = []
        insights = []
        matches = 0

        # Get recent command history
        history = context.get("history", [])[-5:]  # Last 5 commands

        # Check for workflow patterns
        for workflow_name, steps in self.workflow_patterns.items():
            if self._match_workflow(steps, history + [command]):
                matches += 1
                patterns.append({
                    "workflow": workflow_name,
                    "steps": steps,
                    "current_step": command
                })
                insights.append(f"Command is part of {workflow_name} workflow")

        # Check for repeated patterns
        repeated = self._find_repeated_patterns(history + [command])
        if repeated:
            patterns.extend(repeated)
            insights.append("Detected repeated command pattern")
            matches += len(repeated)

        # Calculate confidence
        confidence = self._calculate_confidence(matches, len(self.workflow_patterns))

        return AnalysisResult(
            confidence=confidence,
            patterns=patterns,
            insights=insights,
            metadata={
                "timestamp": time.time(),
                "history_length": len(history)
            }
        )

    def _match_workflow(self, workflow: List[str], history: List[str]) -> bool:
        """Check if command history matches workflow pattern"""
        workflow_str = "|".join(workflow)
        history_str = "|".join(history)
        return workflow_str in history_str

    def _find_repeated_patterns(self, history: List[str]) -> List[Dict]:
        """Find repeated command patterns in history"""
        patterns = []
        for i in range(len(history)-1):
            for j in range(i+1, len(history)):
                if history[i] == history[j]:
                    patterns.append({
                        "type": "repetition",
                        "command": history[i],
                        "positions": [i, j]
                    })
        return patterns

class ContextAnalyzer(BaseAnalyzer):
    """Analyzes command context and environment"""

    def __init__(self):
        super().__init__()
        self.context_patterns = {
            "path_aware": r"\$PWD|\$HOME|~/|\.{1,2}/",
            "env_vars": r"\$\w+",
            "dynamic_refs": r"\$\(\w+\)|\`\w+\`",
            "conditional": r"if|test|case|while"
        }

    async def analyze(self, command: str, context: Dict) -> AnalysisResult:
        """Analyze command context awareness"""
        patterns = []
        insights = []
        matches = 0

        # Check for context-aware patterns
        for category, pattern in self.context_patterns.items():
            if re.search(pattern, command):
                matches += 1
                patterns.append({
                    "category": category,
                    "pattern": pattern,
                    "command": command
                })
                insights.append(f"Command uses {category} context")

        # Check working directory relevance
        cwd = context.get("cwd", "")
        if cwd in command:
            patterns.append({
                "category": "cwd_aware",
                "cwd": cwd,
                "command": command
            })
            insights.append("Command references current directory")
            matches += 1

        # Check environment variable usage
        env = context.get("env", {})
        for var in env:
            if f"${var}" in command:
                patterns.append({
                    "category": "env_aware",
                    "variable": var,
                    "command": command
                })
                insights.append(f"Command uses {var} environment variable")
                matches += 1

        # Calculate confidence
        total_patterns = len(self.context_patterns) + 2  # +2 for cwd and env checks
        confidence = self._calculate_confidence(matches, total_patterns)

        return AnalysisResult(
            confidence=confidence,
            patterns=patterns,
            insights=insights,
            metadata={
                "timestamp": time.time(),
                "cwd": cwd,
                "env_vars": list(env.keys())
            }
        )
