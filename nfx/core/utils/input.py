"""NFX Input Module

Advanced input handling for NFX with integrated AutoGPT functionality.
Includes keyboard input, neural input, and quantum state input handling.
"""
import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt

logger = logging.getLogger(__name__)
console = Console()

class InputType(str, Enum):
    """Types of input supported"""
    TEXT = "text"
    CONFIRM = "confirm"
    PASSWORD = "password"
    NUMBER = "number"
    NEURAL = "neural"
    QUANTUM = "quantum"

class InputResult:
    """Result of input operation"""
    def __init__(
        self,
        value: Any,
        input_type: InputType,
        timestamp: datetime = None,
        metadata: Dict = None
    ):
        self.value = value
        self.input_type = input_type
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"InputResult(value={self.value}, type={self.input_type})"

class InputHandler:
    """Handles various types of input"""

    def __init__(self):
        self.history: List[InputResult] = []
        self._neural_patterns = {}
        self._quantum_states = {}

    def clean_input(self, prompt: str = "", default: str = "") -> InputResult:
        """Get clean text input from user"""
        try:
            value = click.prompt(
                text=prompt,
                prompt_suffix=" ",
                default=default,
                show_default=bool(default)
            )
            result = InputResult(value, InputType.TEXT)
            self.history.append(result)
            return result

        except KeyboardInterrupt:
            logger.info("Input interrupted")
            raise

    def confirm(
        self,
        prompt: str,
        default: bool = True,
        show_default: bool = True
    ) -> InputResult:
        """Get confirmation from user"""
        try:
            value = Confirm.ask(
                prompt,
                default=default,
                show_default=show_default
            )
            result = InputResult(value, InputType.CONFIRM)
            self.history.append(result)
            return result

        except KeyboardInterrupt:
            logger.info("Input interrupted")
            raise

    def password(
        self,
        prompt: str = "Enter password",
        confirm: bool = True
    ) -> InputResult:
        """Get password input"""
        try:
            value = click.prompt(
                text=prompt,
                hide_input=True,
                confirmation_prompt=confirm
            )
            result = InputResult(value, InputType.PASSWORD)
            self.history.append(result)
            return result

        except KeyboardInterrupt:
            logger.info("Input interrupted")
            raise

    def number(
        self,
        prompt: str,
        min_value: float = None,
        max_value: float = None,
        default: float = None
    ) -> InputResult:
        """Get numeric input"""
        try:
            value = click.prompt(
                text=prompt,
                type=float,
                default=default,
                show_default=bool(default)
            )

            if min_value is not None and value < min_value:
                raise ValueError(f"Value must be >= {min_value}")

            if max_value is not None and value > max_value:
                raise ValueError(f"Value must be <= {max_value}")

            result = InputResult(value, InputType.NUMBER)
            self.history.append(result)
            return result

        except KeyboardInterrupt:
            logger.info("Input interrupted")
            raise

    def register_neural_pattern(self, name: str, pattern: List[int]) -> None:
        """Register a neural input pattern"""
        if not all(x in (0, 1) for x in pattern):
            raise ValueError("Pattern must contain only 0s and 1s")
        self._neural_patterns[name] = pattern

    def neural_input(self, prompt: str, pattern_name: str) -> InputResult:
        """Get neural pattern input"""
        if pattern_name not in self._neural_patterns:
            raise ValueError(f"Unknown pattern: {pattern_name}")

        expected = self._neural_patterns[pattern_name]
        console.print(f"[cyan]Expected pattern:[/] {expected}")

        try:
            value = click.prompt(
                text=prompt,
                value_proc=lambda x: [int(i) for i in x.split()]
            )

            if value == expected:
                result = InputResult(
                    value,
                    InputType.NEURAL,
                    metadata={"pattern_name": pattern_name}
                )
                self.history.append(result)
                return result
            else:
                raise ValueError("Pattern mismatch")

        except KeyboardInterrupt:
            logger.info("Input interrupted")
            raise

    def register_quantum_state(self, name: str, state: complex) -> None:
        """Register a quantum state"""
        self._quantum_states[name] = state

    def quantum_input(self, prompt: str, state_name: str) -> InputResult:
        """Get quantum state input"""
        if state_name not in self._quantum_states:
            raise ValueError(f"Unknown quantum state: {state_name}")

        expected = self._quantum_states[state_name]
        console.print(f"[cyan]Expected state:[/] {expected}")

        try:
            real = click.prompt("Enter real part", type=float)
            imag = click.prompt("Enter imaginary part", type=float)
            value = complex(real, imag)

            if abs(value - expected) < 1e-6:
                result = InputResult(
                    value,
                    InputType.QUANTUM,
                    metadata={"state_name": state_name}
                )
                self.history.append(result)
                return result
            else:
                raise ValueError("Quantum state mismatch")

        except KeyboardInterrupt:
            logger.info("Input interrupted")
            raise

    def get_history(
        self,
        input_type: Optional[InputType] = None,
        limit: Optional[int] = None
    ) -> List[InputResult]:
        """Get input history"""
        history = self.history

        if input_type:
            history = [x for x in history if x.input_type == input_type]

        if limit:
            history = history[-limit:]

        return history

    def clear_history(self) -> None:
        """Clear input history"""
        self.history.clear()

# Global input handler instance
input_handler = InputHandler()
