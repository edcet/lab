"""TGPT Integration with shell command optimization"""

import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import logging
from cachetools import TTLCache
import subprocess
import shlex
import re

class TGPTExecutor:
    """Optimized TGPT command executor"""
    
    def __init__(self, provider: str = "ollama"):
        self.provider = provider
        self.command_cache = TTLCache(maxsize=1000, ttl=3600)
        self.unsafe_patterns = [
            r"rm\s+-rf",
            r"mkfs",
            r"dd\s+if=",
            r">\s*/dev",
            r"chmod\s+777",
            r"sudo",
            r";\s*rm",
            r";\s*dd",
            r";\s*mkfs"
        ]
        self.logger = logging.getLogger(__name__)
        self.metrics = {
            'commands_executed': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_duration': 0
        }

    async def initialize(self) -> bool:
        """Initialize executor"""
        try:
            # Verify tgpt installation
            result = await self._run_command(['tgpt', '--version'])
            if result['exit_code'] != 0:
                raise RuntimeError("TGPT not installed or not accessible")
            return True
        except Exception as e:
            self.logger.error(f"TGPT initialization failed: {e}")
            return False

    async def execute_shell(self, 
                         prompt: str, 
                         auto_approve: bool = False,
                         **kwargs) -> Dict[str, Any]:
        """Execute shell command through TGPT"""
        cache_key = self._get_cache_key(prompt, kwargs)
        
        # Check cache for identical commands
        if cached := self.command_cache.get(cache_key):
            self.metrics['cache_hits'] += 1
            return cached

        start_time = datetime.now()
        try:
            # Generate command first
            command = await self._generate_command(prompt)
            
            # Validate command safety
            if not self._is_safe_command(command):
                raise ValueError(f"Unsafe command detected: {command}")
            
            # Execute command
            flags = ['-s']  # Shell mode
            if auto_approve:
                flags.append('-y')
            
            result = await self._execute_tgpt(
                flags=flags,
                provider=self.provider,
                command=command
            )
            
            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics['commands_executed'] += 1
            self.metrics['total_duration'] += duration
            
            # Cache result
            self.command_cache[cache_key] = result
            return result

        except Exception as e:
            self.metrics['errors'] += 1
            self.logger.error(f"Command execution failed: {e}")
            raise

    async def _generate_command(self, prompt: str) -> str:
        """Generate shell command from prompt"""
        try:
            flags = ['-s', '-q']  # Shell mode, quiet output
            result = await self._execute_tgpt(
                flags=flags,
                provider=self.provider,
                prompt=prompt,
                command_only=True
            )
            return result['output'].strip()
        except Exception as e:
            self.logger.error(f"Command generation failed: {e}")
            raise

    def _is_safe_command(self, command: str) -> bool:
        """Validate command safety"""
        command = command.lower()
        return not any(
            re.search(pattern, command)
            for pattern in self.unsafe_patterns
        )

    async def _execute_tgpt(self, 
                          flags: List[str], 
                          provider: str,
                          command: Optional[str] = None,
                          prompt: Optional[str] = None,
                          command_only: bool = False) -> Dict[str, Any]:
        """Execute TGPT with given flags"""
        cmd = ['tgpt'] + flags + ['--provider', provider]
        
        if command:
            cmd.append(command)
        elif prompt:
            cmd.append(prompt)
        
        try:
            result = await self._run_command(cmd)
            if result['exit_code'] != 0:
                raise RuntimeError(f"TGPT execution failed: {result['stderr']}")
            return result
        except Exception as e:
            self.logger.error(f"TGPT execution error: {e}")
            raise

    async def _run_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Run shell command asynchronously"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        return {
            'output': stdout.decode().strip(),
            'stderr': stderr.decode().strip(),
            'exit_code': process.returncode
        }

    def _get_cache_key(self, prompt: str, kwargs: Dict) -> str:
        """Generate cache key for command"""
        return f"{prompt}|{self.provider}|{str(sorted(kwargs.items()))}"

    async def get_metrics(self) -> Dict[str, Any]:
        """Get executor metrics"""
        avg_duration = (
            self.metrics['total_duration'] / 
            max(1, self.metrics['commands_executed'])
        )
        
        return {
            **self.metrics,
            'average_duration': avg_duration,
            'cache_hit_ratio': (
                self.metrics['cache_hits'] / 
                max(1, self.metrics['commands_executed'])
            ),
            'error_rate': (
                self.metrics['errors'] / 
                max(1, self.metrics['commands_executed'])
            )
        }

    async def cleanup(self):
        """Cleanup executor resources"""
        self.command_cache.clear()
