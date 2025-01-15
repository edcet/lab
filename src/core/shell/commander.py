"""Unified Shell Command System

This module implements a comprehensive shell command system that consolidates:
- Command execution and management
- Process control
- Output streaming
- Error handling
- Resource limits
- Security checks
"""

import asyncio
import subprocess
from typing import Dict, List, Set, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import shlex
import os
import signal
import psutil
from pathlib import Path
from enum import Enum

logger = logging.getLogger("shell.commander")

class CommandType(Enum):
    """Types of commands supported"""
    SHELL = "shell"
    PYTHON = "python"
    NODE = "node"
    CUSTOM = "custom"

@dataclass
class CommandConfig:
    """Command execution configuration"""
    timeout: float = 30.0
    max_output: int = 1024 * 1024  # 1MB
    max_memory: int = 512 * 1024 * 1024  # 512MB
    allowed_paths: Set[Path] = field(default_factory=set)
    blocked_commands: Set[str] = field(default_factory=set)
    environment: Dict[str, str] = field(default_factory=dict)

@dataclass
class CommandContext:
    """Command execution context"""
    command_id: str
    command_type: CommandType
    working_dir: Path
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

@dataclass
class CommandResult:
    """Command execution result"""
    command_id: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    peak_memory: int
    error: Optional[str] = None

class CommandValidator:
    """Command validation and security checks"""

    def __init__(self, config: CommandConfig):
        self.config = config

    def validate_command(self, command: str, context: CommandContext) -> bool:
        """Validate command against security policies"""
        try:
            # Split command into parts
            parts = shlex.split(command)
            if not parts:
                return False

            # Check blocked commands
            if parts[0] in self.config.blocked_commands:
                logger.warning(f"Blocked command attempted: {parts[0]}")
                return False

            # Check paths
            if self.config.allowed_paths:
                cmd_path = Path(parts[0])
                if not any(
                    allowed.resolve() in cmd_path.resolve().parents
                    for allowed in self.config.allowed_paths
                ):
                    logger.warning(f"Command outside allowed paths: {cmd_path}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Command validation error: {e}")
            return False

class ProcessManager:
    """Process execution and management"""

    def __init__(self, config: CommandConfig):
        self.config = config
        self.active_processes: Dict[str, subprocess.Process] = {}
        self._monitor_task = asyncio.create_task(self._monitor_processes())

    async def execute(self,
                     command: str,
                     context: CommandContext) -> AsyncGenerator[str, None]:
        """Execute command and stream output"""
        try:
            # Create process
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=context.working_dir,
                env=self.config.environment,
                preexec_fn=os.setsid  # Create new process group
            )

            self.active_processes[context.command_id] = process

            try:
                # Stream output
                async for line in self._stream_output(process):
                    yield line

            finally:
                # Cleanup
                await self._cleanup_process(context.command_id)

        except Exception as e:
            logger.error(f"Process execution error: {e}")
            raise

    async def _stream_output(self,
                           process: subprocess.Process) -> AsyncGenerator[str, None]:
        """Stream process output"""
        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode().rstrip()

        except Exception as e:
            logger.error(f"Output streaming error: {e}")
            raise

    async def _cleanup_process(self, command_id: str):
        """Cleanup process resources"""
        try:
            process = self.active_processes.pop(command_id, None)
            if process:
                try:
                    # Kill entire process group
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass  # Process already terminated

        except Exception as e:
            logger.error(f"Process cleanup error: {e}")

    async def _monitor_processes(self):
        """Monitor active processes"""
        while True:
            try:
                for command_id, process in list(self.active_processes.items()):
                    try:
                        # Check process resources
                        proc = psutil.Process(process.pid)
                        memory_info = proc.memory_info()

                        # Check memory limit
                        if memory_info.rss > self.config.max_memory:
                            logger.warning(
                                f"Process {command_id} exceeded memory limit"
                            )
                            await self._cleanup_process(command_id)

                    except psutil.NoSuchProcess:
                        # Process already terminated
                        await self._cleanup_process(command_id)

                await asyncio.sleep(1)  # Check every second

            except Exception as e:
                logger.error(f"Process monitoring error: {e}")
                await asyncio.sleep(5)  # Back off on error

class CommandManager:
    """Unified shell command manager"""

    def __init__(self, config: CommandConfig):
        # Core components
        self.config = config
        self.validator = CommandValidator(config)
        self.process_manager = ProcessManager(config)

        # Command tracking
        self.command_history: List[CommandResult] = []
        self.active_commands: Dict[str, CommandContext] = {}

    async def execute_command(self,
                            command: str,
                            command_type: CommandType,
                            working_dir: Path,
                            metadata: Dict = None) -> CommandResult:
        """Execute a command"""
        try:
            # Generate command ID
            command_id = f"{command_type.value}_{datetime.now().timestamp()}"

            # Create context
            context = CommandContext(
                command_id=command_id,
                command_type=command_type,
                working_dir=working_dir,
                metadata=metadata or {}
            )

            # Validate command
            if not self.validator.validate_command(command, context):
                return CommandResult(
                    command_id=command_id,
                    exit_code=-1,
                    stdout="",
                    stderr="Command validation failed",
                    duration=0.0,
                    peak_memory=0,
                    error="Command validation failed"
                )

            # Track command
            self.active_commands[command_id] = context

            # Execute with timeout
            start_time = datetime.now()
            output = []
            peak_memory = 0

            try:
                async with asyncio.timeout(self.config.timeout):
                    async for line in self.process_manager.execute(command, context):
                        output.append(line)

                        # Check output size
                        if sum(len(l) for l in output) > self.config.max_output:
                            raise ValueError("Maximum output size exceeded")

            except asyncio.TimeoutError:
                error = "Command execution timed out"
            except ValueError as e:
                error = str(e)
            except Exception as e:
                error = f"Command execution failed: {e}"
            else:
                error = None

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            # Create result
            result = CommandResult(
                command_id=command_id,
                exit_code=0 if not error else -1,
                stdout="\n".join(output),
                stderr=error or "",
                duration=duration,
                peak_memory=peak_memory,
                error=error
            )

            # Update history
            self.command_history.append(result)
            if len(self.command_history) > 1000:  # Keep last 1000 commands
                self.command_history = self.command_history[-1000:]

            return result

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            raise
        finally:
            # Cleanup
            self.active_commands.pop(command_id, None)

    async def get_command_history(self,
                                command_type: Optional[CommandType] = None,
                                start_time: Optional[datetime] = None,
                                end_time: Optional[datetime] = None) -> List[CommandResult]:
        """Get command execution history"""
        filtered = []
        for result in self.command_history:
            # Filter by type
            if command_type and self.active_commands[result.command_id].command_type != command_type:
                continue

            # Filter by time
            created_at = self.active_commands[result.command_id].created_at
            if start_time and created_at < start_time:
                continue
            if end_time and created_at > end_time:
                continue

            filtered.append(result)

        return filtered

    def get_active_commands(self) -> Dict[str, CommandContext]:
        """Get currently active commands"""
        return self.active_commands.copy()

    async def terminate_command(self, command_id: str):
        """Terminate a running command"""
        try:
            if command_id not in self.active_commands:
                raise ValueError(f"Command not found: {command_id}")

            await self.process_manager._cleanup_process(command_id)

        except Exception as e:
            logger.error(f"Command termination error: {e}")
            raise
