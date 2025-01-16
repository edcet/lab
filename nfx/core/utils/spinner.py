"""NFX Spinner Module

Advanced progress indication for NFX with integrated AutoGPT functionality.
Includes spinners, progress bars, and neural activity indicators.
"""
import asyncio
import itertools
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.spinner import Spinner as RichSpinner

console = Console()

class SpinnerStyle(str, Enum):
    """Available spinner styles"""
    CLASSIC = "classic"  # Classic ASCII spinner
    DOTS = "dots"  # Unicode dots
    LINE = "line"  # Unicode line
    PULSE = "pulse"  # Unicode pulse
    NEURAL = "neural"  # Neural activity pattern
    QUANTUM = "quantum"  # Quantum state evolution

@dataclass
class SpinnerState:
    """State of a spinner"""
    message: str
    start_time: datetime
    style: SpinnerStyle
    metadata: Dict[str, Any]

class Spinner:
    """Advanced spinner with multiple styles and neural indicators"""

    # Spinner patterns
    PATTERNS = {
        SpinnerStyle.CLASSIC: ["-", "/", "|", "\\"],
        SpinnerStyle.DOTS: ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        SpinnerStyle.LINE: ["⠂", "⠄", "⠆", "⠇", "⠋", "⠙", "⠸", "⠰", "⠠", "⠰"],
        SpinnerStyle.PULSE: ["█", "▉", "▊", "▋", "▌", "▍", "▎", "▏", "▎", "▍", "▌", "▋", "▊", "▉"],
        SpinnerStyle.NEURAL: ["⚡", "🧠", "⚡", "💭", "⚡"],
        SpinnerStyle.QUANTUM: ["⟩", "⟨", "⟩", "⟨", "⟩"]
    }

    def __init__(
        self,
        message: str = "Loading...",
        style: SpinnerStyle = SpinnerStyle.CLASSIC,
        delay: float = 0.1,
        neural_activity: bool = False,
        quantum_state: bool = False,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Initialize spinner

        Args:
            message: Message to display
            style: Spinner style to use
            delay: Delay between updates
            neural_activity: Show neural activity indicator
            quantum_state: Show quantum state indicator
            metadata: Additional metadata
        """
        self.state = SpinnerState(
            message=message,
            start_time=datetime.now(),
            style=style,
            metadata=metadata or {}
        )
        self.delay = delay
        self.neural_activity = neural_activity
        self.quantum_state = quantum_state
        self.running = False
        self.spinner_thread = None
        self._spinner_iter = itertools.cycle(self.PATTERNS[style])

        # Rich progress
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            TimeElapsedColumn(),
            console=console
        )
        self.task_id = None

    def _get_neural_indicator(self) -> str:
        """Get neural activity indicator"""
        if not self.neural_activity:
            return ""
        activity = abs(hash(str(time.time()))) % 100
        bars = "▁▂▃▄▅▆▇█"
        index = int((activity / 100) * (len(bars) - 1))
        return f" [cyan]{bars[index]}[/]"

    def _get_quantum_indicator(self) -> str:
        """Get quantum state indicator"""
        if not self.quantum_state:
            return ""
        t = time.time()
        phase = abs(hash(str(t))) % 360
        indicator = "●" if phase < 180 else "○"
        return f" [magenta]{indicator}[/]"

    def spin(self) -> None:
        """Spin the spinner"""
        if not self.task_id:
            self.task_id = self.progress.add_task(
                self.state.message,
                total=None
            )

        while self.running:
            # Update spinner frame
            frame = next(self._spinner_iter)

            # Get indicators
            neural = self._get_neural_indicator()
            quantum = self._get_quantum_indicator()

            # Update message
            message = f"{self.state.message}{neural}{quantum}"
            self.progress.update(self.task_id, description=message)

            time.sleep(self.delay)

    def start(self) -> None:
        """Start the spinner"""
        self.running = True
        self.progress.start()
        self.spinner_thread = threading.Thread(target=self.spin)
        self.spinner_thread.start()

    def stop(self) -> None:
        """Stop the spinner"""
        self.running = False
        if self.spinner_thread:
            self.spinner_thread.join()
        if self.task_id is not None:
            self.progress.remove_task(self.task_id)
        self.progress.stop()

    def update(
        self,
        message: Optional[str] = None,
        style: Optional[SpinnerStyle] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update spinner state

        Args:
            message: New message
            style: New style
            metadata: New metadata
        """
        if message:
            self.state.message = message

        if style:
            self.state.style = style
            self._spinner_iter = itertools.cycle(self.PATTERNS[style])

        if metadata:
            self.state.metadata.update(metadata)

    def __enter__(self) -> "Spinner":
        """Start spinner as context manager"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop spinner when exiting context"""
        self.stop()

class MultiSpinner:
    """Manages multiple spinners"""

    def __init__(self):
        self.spinners: Dict[str, Spinner] = {}

    def add(
        self,
        name: str,
        message: str,
        style: SpinnerStyle = SpinnerStyle.CLASSIC,
        **kwargs
    ) -> Spinner:
        """Add a new spinner

        Args:
            name: Unique name for spinner
            message: Spinner message
            style: Spinner style
            **kwargs: Additional spinner options
        """
        if name in self.spinners:
            raise ValueError(f"Spinner {name} already exists")

        spinner = Spinner(message, style, **kwargs)
        self.spinners[name] = spinner
        return spinner

    def get(self, name: str) -> Optional[Spinner]:
        """Get spinner by name"""
        return self.spinners.get(name)

    def remove(self, name: str) -> None:
        """Remove and stop a spinner"""
        if spinner := self.spinners.pop(name, None):
            spinner.stop()

    def start_all(self) -> None:
        """Start all spinners"""
        for spinner in self.spinners.values():
            spinner.start()

    def stop_all(self) -> None:
        """Stop all spinners"""
        for spinner in self.spinners.values():
            spinner.stop()
        self.spinners.clear()

    def __enter__(self) -> "MultiSpinner":
        """Start all spinners as context manager"""
        self.start_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop all spinners when exiting context"""
        self.stop_all()

# Global spinner manager
spinner_manager = MultiSpinner()
