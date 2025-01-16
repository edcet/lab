"""NFX Tool Integration Module

Advanced tool integration for NFX with local LLM tools.
Handles interactions with Ollama, LM Studio, TGPT, and other tools.
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set
import aiohttp

logger = logging.getLogger(__name__)

class ToolType(str, Enum):
    """Available tool types"""
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    TGPT = "tgpt"
    INTERPRETER = "interpreter"
    AUTOGPT = "autogpt"

@dataclass
class ToolConfig:
    """Tool configuration"""
    type: ToolType
    endpoint: str
    models: List[str]
    capabilities: Set[str]
    priority: int = 1
    max_tokens: int = 4096
    temperature: float = 0.7

@dataclass
class ToolResponse:
    """Response from tool execution"""
    text: str
    tool: ToolType
    model: str
    timestamp: datetime
    metadata: Dict[str, Any]

class ToolIntegration:
    """Handles integration with local LLM tools"""

    def __init__(self):
        # Initialize tool configurations
        self.tools: Dict[ToolType, ToolConfig] = {
            ToolType.OLLAMA: ToolConfig(
                type=ToolType.OLLAMA,
                endpoint="http://localhost:11434",
                models=["codellama", "llama2"],
                capabilities={"code_generation", "code_analysis", "pattern_detection"},
                priority=1
            ),
            ToolType.LM_STUDIO: ToolConfig(
                type=ToolType.LM_STUDIO,
                endpoint="http://localhost:1234",
                models=["mixtral"],
                capabilities={"code_generation", "text_generation", "pattern_analysis"},
                priority=2
            ),
            ToolType.TGPT: ToolConfig(
                type=ToolType.TGPT,
                endpoint="http://localhost:4891",
                models=["gpt4"],
                capabilities={"shell_execution", "documentation", "automation"},
                priority=3
            )
        }

        # Track tool states
        self.tool_states: Dict[ToolType, bool] = {
            tool: False for tool in ToolType
        }

        self._logger = logging.getLogger("tool_integration")

    async def initialize(self) -> None:
        """Initialize tool connections"""
        for tool_type, config in self.tools.items():
            try:
                if await self._check_tool_availability(tool_type, config):
                    self.tool_states[tool_type] = True
                    self._logger.info(f"{tool_type} initialized successfully")
                else:
                    self._logger.warning(f"{tool_type} not available")
            except Exception as e:
                self._logger.error(f"Error initializing {tool_type}: {e}")

    async def _check_tool_availability(self, tool_type: ToolType, config: ToolConfig) -> bool:
        """Check if tool is available"""
        try:
            if tool_type == ToolType.OLLAMA:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{config.endpoint}/api/tags") as resp:
                        return resp.status == 200

            elif tool_type == ToolType.LM_STUDIO:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{config.endpoint}/v1/models") as resp:
                        return resp.status == 200

            elif tool_type == ToolType.TGPT:
                # Check TGPT using shell command
                result = subprocess.run(
                    ["tgpt", "-s", "echo test", "-y"],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0

            return False

        except Exception as e:
            self._logger.error(f"Error checking {tool_type} availability: {e}")
            return False

    async def execute_with_tool(
        self,
        tool_type: ToolType,
        input_text: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Optional[ToolResponse]:
        """Execute input with specified tool"""
        if not self.tool_states.get(tool_type):
            self._logger.error(f"{tool_type} not available")
            return None

        config = self.tools[tool_type]
        try:
            if tool_type == ToolType.OLLAMA:
                return await self._execute_ollama(input_text, model or config.models[0])

            elif tool_type == ToolType.LM_STUDIO:
                return await self._execute_lm_studio(
                    input_text,
                    model or config.models[0],
                    system_prompt
                )

            elif tool_type == ToolType.TGPT:
                return await self._execute_tgpt(input_text)

            self._logger.error(f"Unknown tool type: {tool_type}")
            return None

        except Exception as e:
            self._logger.error(f"Error executing with {tool_type}: {e}")
            return None

    async def _execute_ollama(self, input_text: str, model: str) -> Optional[ToolResponse]:
        """Execute with Ollama"""
        config = self.tools[ToolType.OLLAMA]
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": model,
                    "prompt": input_text,
                    "temperature": config.temperature,
                    "num_predict": config.max_tokens
                }

                async with session.post(
                    f"{config.endpoint}/api/generate",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return ToolResponse(
                            text=result["response"],
                            tool=ToolType.OLLAMA,
                            model=model,
                            timestamp=datetime.now(),
                            metadata=result
                        )

            return None

        except Exception as e:
            self._logger.error(f"Ollama execution failed: {e}")
            return None

    async def _execute_lm_studio(
        self,
        input_text: str,
        model: str,
        system_prompt: Optional[str] = None
    ) -> Optional[ToolResponse]:
        """Execute with LM Studio"""
        config = self.tools[ToolType.LM_STUDIO]
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "prompt": input_text,
                    "system_prompt": system_prompt if system_prompt else "",
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens
                }

                async with session.post(
                    f"{config.endpoint}/v1/completions",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return ToolResponse(
                            text=result["choices"][0]["text"],
                            tool=ToolType.LM_STUDIO,
                            model=model,
                            timestamp=datetime.now(),
                            metadata=result
                        )

            return None

        except Exception as e:
            self._logger.error(f"LM Studio execution failed: {e}")
            return None

    async def _execute_tgpt(self, input_text: str) -> Optional[ToolResponse]:
        """Execute with TGPT"""
        try:
            result = subprocess.run(
                ["tgpt", "-s", input_text, "-y"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return ToolResponse(
                    text=result.stdout,
                    tool=ToolType.TGPT,
                    model="gpt4",
                    timestamp=datetime.now(),
                    metadata={
                        "returncode": result.returncode,
                        "stderr": result.stderr
                    }
                )

            return None

        except Exception as e:
            self._logger.error(f"TGPT execution failed: {e}")
            return None

    async def select_tool(
        self,
        input_text: str,
        required_capabilities: Set[str]
    ) -> Optional[ToolType]:
        """Select best tool based on capabilities and availability"""
        available_tools = [
            tool_type for tool_type, available in self.tool_states.items()
            if available
        ]

        if not available_tools:
            return None

        # Score each available tool
        tool_scores = []
        for tool_type in available_tools:
            config = self.tools[tool_type]
            capability_score = len(
                required_capabilities.intersection(config.capabilities)
            )
            tool_scores.append((tool_type, capability_score, config.priority))

        if not tool_scores:
            return None

        # Select tool with highest capability score and priority
        selected_tool = max(
            tool_scores,
            key=lambda x: (x[1], -x[2])  # Higher score, lower priority number
        )[0]

        return selected_tool

    async def cleanup(self) -> None:
        """Cleanup tool resources"""
        # Nothing to clean up for now
        pass
