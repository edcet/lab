"""NFX LLM Interface Module

Advanced local LLM integration with parallel execution capabilities.
Provides interfaces to LM Studio and Ollama for autonomous operations.
"""

import asyncio
import json
import logging
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import aiohttp
import numpy as np

@dataclass
class LLMResponse:
    """Response from LLM model"""
    text: str
    model: str
    timestamp: datetime
    metadata: Dict[str, Any]

class LLMInterface:
    """Interface for local LLM tools"""

    def __init__(self):
        self._logger = logging.getLogger('llm_interface')
        self.lm_studio_url = "http://localhost:1234/v1"
        self.ollama_url = "http://localhost:11434/api"

        # Initialize model configs
        self.lm_studio_config = {
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.95
        }

        self.ollama_config = {
            "temperature": 0.7,
            "num_predict": 2048,
            "top_p": 0.95
        }

        # Track active sessions
        self.active_sessions = {}

    async def init_lm_studio(self):
        """Initialize LM Studio connection"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.lm_studio_url}/models") as resp:
                    if resp.status == 200:
                        self._logger.info("LM Studio initialized successfully")
                        return True
                    else:
                        self._logger.error("Failed to initialize LM Studio")
                        return False
        except Exception as e:
            self._logger.error(f"Error initializing LM Studio: {e}")
            return False

    async def init_ollama(self):
        """Initialize Ollama connection"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/tags") as resp:
                    if resp.status == 200:
                        self._logger.info("Ollama initialized successfully")
                        return True
                    else:
                        self._logger.error("Failed to initialize Ollama")
                        return False
        except Exception as e:
            self._logger.error(f"Error initializing Ollama: {e}")
            return False

    async def query_lm_studio(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Query LM Studio model"""
        try:
            payload = {
                "prompt": prompt,
                "system_prompt": system_prompt if system_prompt else "",
                **self.lm_studio_config
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.lm_studio_url}/completions", json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return LLMResponse(
                            text=result["choices"][0]["text"],
                            model="lm_studio",
                            timestamp=datetime.now(),
                            metadata=result
                        )
                    else:
                        raise Exception(f"LM Studio query failed with status {resp.status}")

        except Exception as e:
            self._logger.error(f"Error querying LM Studio: {e}")
            raise

    async def query_ollama(self, prompt: str, model: str = "llama2") -> LLMResponse:
        """Query Ollama model"""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                **self.ollama_config
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.ollama_url}/generate", json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return LLMResponse(
                            text=result["response"],
                            model=f"ollama_{model}",
                            timestamp=datetime.now(),
                            metadata=result
                        )
                    else:
                        raise Exception(f"Ollama query failed with status {resp.status}")

        except Exception as e:
            self._logger.error(f"Error querying Ollama: {e}")
            raise

    async def parallel_query(self, prompt: str, system_prompt: Optional[str] = None) -> List[LLMResponse]:
        """Query both LM Studio and Ollama in parallel"""
        try:
            tasks = [
                self.query_lm_studio(prompt, system_prompt),
                self.query_ollama(prompt)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            valid_results = []
            for result in results:
                if isinstance(result, Exception):
                    self._logger.error(f"Query failed: {result}")
                else:
                    valid_results.append(result)

            return valid_results

        except Exception as e:
            self._logger.error(f"Error in parallel query: {e}")
            raise

    async def autonomous_task(self, task_description: str) -> Dict[str, Any]:
        """Execute autonomous task using both LLMs"""
        try:
            # Get responses from both models
            responses = await self.parallel_query(
                prompt=f"Task: {task_description}\nPlease provide detailed steps to accomplish this task.",
                system_prompt="You are an AI assistant helping to complete development tasks."
            )

            # Analyze and combine responses
            combined_response = {
                "task": task_description,
                "timestamp": datetime.now(),
                "responses": responses,
                "analysis": self._analyze_responses(responses),
                "suggested_actions": self._extract_actions(responses)
            }

            return combined_response

        except Exception as e:
            self._logger.error(f"Error in autonomous task: {e}")
            raise

    def _analyze_responses(self, responses: List[LLMResponse]) -> Dict[str, Any]:
        """Analyze responses from different models"""
        analysis = {
            "agreement_level": self._calculate_agreement(responses),
            "confidence_scores": self._calculate_confidence(responses),
            "unique_suggestions": self._extract_unique_suggestions(responses)
        }
        return analysis

    def _calculate_agreement(self, responses: List[LLMResponse]) -> float:
        """Calculate agreement level between responses"""
        if len(responses) < 2:
            return 1.0

        # Simple text similarity for now
        text1 = responses[0].text.lower()
        text2 = responses[1].text.lower()

        words1 = set(text1.split())
        words2 = set(text2.split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def _calculate_confidence(self, responses: List[LLMResponse]) -> Dict[str, float]:
        """Calculate confidence scores for responses"""
        confidence_scores = {}

        for response in responses:
            # Calculate based on response metadata and content
            score = 1.0

            # Adjust based on response length
            score *= min(len(response.text.split()) / 100, 1.0)

            # Adjust based on specificity
            if any(word in response.text.lower() for word in ["maybe", "perhaps", "might"]):
                score *= 0.8

            confidence_scores[response.model] = score

        return confidence_scores

    def _extract_unique_suggestions(self, responses: List[LLMResponse]) -> List[str]:
        """Extract unique suggestions from responses"""
        all_suggestions = []

        for response in responses:
            # Split into sentences and filter for actionable items
            sentences = response.text.split(".")
            suggestions = [
                s.strip() for s in sentences
                if any(word in s.lower() for word in ["should", "could", "must", "need", "implement", "create", "add"])
            ]
            all_suggestions.extend(suggestions)

        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in all_suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)

        return unique_suggestions

    def _extract_actions(self, responses: List[LLMResponse]) -> List[Dict[str, Any]]:
        """Extract concrete actions from responses"""
        actions = []

        for response in responses:
            # Look for specific action patterns
            lines = response.text.split("\n")

            for line in lines:
                if any(word in line.lower() for word in ["implement", "create", "add", "modify", "update"]):
                    action = {
                        "type": "code_change",
                        "description": line.strip(),
                        "source_model": response.model,
                        "priority": self._estimate_priority(line)
                    }
                    actions.append(action)

        return sorted(actions, key=lambda x: x["priority"], reverse=True)

    def _estimate_priority(self, action_text: str) -> int:
        """Estimate priority of an action"""
        priority = 1

        # Increase priority for critical terms
        if any(word in action_text.lower() for word in ["critical", "important", "essential", "core"]):
            priority += 2

        # Increase for security/performance terms
        if any(word in action_text.lower() for word in ["security", "performance", "optimization"]):
            priority += 1

        return priority

    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Close any active sessions
            for session in self.active_sessions.values():
                await session.close()

            self.active_sessions.clear()
            self._logger.info("LLM interface cleanup completed")

        except Exception as e:
            self._logger.error(f"Error in cleanup: {e}")
            raise
