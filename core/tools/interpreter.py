"""Open Interpreter Integration with execution optimization"""

import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import logging
from cachetools import TTLCache
import json
import os
import sys

class InterpreterManager:
    """Optimized Open Interpreter execution manager"""
    
    def __init__(self, workspace: str = "./workspace"):
        self.workspace = workspace
        self.code_cache = TTLCache(maxsize=1000, ttl=3600)
        self.interpreter_path = self._find_interpreter()
        self.logger = logging.getLogger(__name__)
        self.metrics = {
            'executions': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_duration': 0
        }
        
        # Execution configuration
        self.config = {
            'auto_run': True,
            'safe_mode': True,
            'max_output_size': 1024 * 1024,  # 1MB
            'timeout': 300  # 5 minutes
        }

    def _find_interpreter(self) -> Optional[str]:
        """Find Open Interpreter installation"""
        paths = os.environ.get('PATH', '').split(os.pathsep)
        for path in paths:
            interpreter = os.path.join(path, 'open-interpreter')
            if os.path.isfile(interpreter):
                return interpreter
        return None

    async def initialize(self) -> bool:
        """Initialize interpreter manager"""
        try:
            if not self.interpreter_path:
                raise RuntimeError("Open Interpreter not found in PATH")
            
            # Create workspace if needed
            os.makedirs(self.workspace, exist_ok=True)
            
            # Verify execution
            test_result = await self.execute_code(
                "print('test')", 
                mode='python'
            )
            return test_result['success']
            
        except Exception as e:
            self.logger.error(f"Interpreter initialization failed: {e}")
            return False

    async def execute_code(self, 
                        code: str, 
                        mode: str = 'python',
                        **kwargs) -> Dict[str, Any]:
        """Execute code through Open Interpreter"""
        cache_key = self._get_cache_key(code, mode, kwargs)
        
        # Check cache
        if cached := self.code_cache.get(cache_key):
            self.metrics['cache_hits'] += 1
            return cached

        start_time = datetime.now()
        try:
            # Prepare execution environment
            env = self._prepare_environment(kwargs)
            
            # Execute code
            process = await asyncio.create_subprocess_exec(
                self.interpreter_path,
                '--run',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=self.workspace
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(code.encode()),
                    timeout=self.config['timeout']
                )
            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError(f"Execution timeout after {self.config['timeout']}s")
            
            result = self._process_output(stdout, stderr, process.returncode)
            
            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics['executions'] += 1
            self.metrics['total_duration'] += duration
            
            # Cache successful results
            if result['success']:
                self.code_cache[cache_key] = result
            
            return result

        except Exception as e:
            self.metrics['errors'] += 1
            self.logger.error(f"Code execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'output': None,
                'duration': (datetime.now() - start_time).total_seconds()
            }

    def _prepare_environment(self, kwargs: Dict) -> Dict[str, str]:
        """Prepare execution environment"""
        env = os.environ.copy()
        
        # Add custom environment variables
        env.update(kwargs.get('env', {}))
        
        # Set execution mode
        env['INTERPRETER_MODE'] = kwargs.get('mode', 'python')
        
        # Set safety flags
        env['INTERPRETER_SAFE_MODE'] = str(self.config['safe_mode']).lower()
        
        return env

    def _process_output(self, 
                     stdout: bytes, 
                     stderr: bytes, 
                     return_code: int) -> Dict[str, Any]:
        """Process execution output"""
        stdout_str = stdout.decode().strip()
        stderr_str = stderr.decode().strip()
        
        # Truncate large output
        if len(stdout_str) > self.config['max_output_size']:
            stdout_str = stdout_str[:self.config['max_output_size']] + "...[truncated]"
        
        return {
            'success': return_code == 0,
            'output': stdout_str if return_code == 0 else None,
            'error': stderr_str if return_code != 0 else None,
            'return_code': return_code
        }

    def _get_cache_key(self, code: str, mode: str, kwargs: Dict) -> str:
        """Generate cache key for execution"""
        return f"{mode}|{code}|{str(sorted(kwargs.items()))}"

    async def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics"""
        avg_duration = (
            self.metrics['total_duration'] / 
            max(1, self.metrics['executions'])
        )
        
        return {
            **self.metrics,
            'average_duration': avg_duration,
            'cache_hit_ratio': (
                self.metrics['cache_hits'] / 
                max(1, self.metrics['executions'])
            ),
            'error_rate': (
                self.metrics['errors'] / 
                max(1, self.metrics['executions'])
            )
        }

    async def cleanup(self):
        """Cleanup interpreter resources"""
        self.code_cache.clear()
