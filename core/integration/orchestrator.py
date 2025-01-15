"""Integration Orchestration System with advanced optimization and safety"""

import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import json
import numpy as np

# Import our components
from ..models.lmstudio import LMStudioClient
from ..models.ollama import OllamaClient
from ..models.jan import JanClient
from ..tools.tgpt import TGPTExecutor
from ..tools.interpreter import InterpreterManager
from ..optimizers.execution import ExecutionOptimizer
from ..optimizers.pipeline import PipelineOptimizer
from ..memory.manager import MemoryManager

@dataclass
class ModelCapabilities:
    """Model capabilities and configuration"""
    name: str
    endpoint: str
    capabilities: List[str]
    max_tokens: int
    streaming: bool = False
    priority: int = 1

@dataclass
class ToolCapabilities:
    """Tool capabilities and configuration"""
    name: str
    capabilities: List[str]
    auto_approve: bool = False
    priority: int = 1

class IntegrationOrchestrator:
    """Orchestrates all tool and model integrations with advanced optimization"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.memory_manager = MemoryManager()
        self.execution_optimizer = ExecutionOptimizer()
        self.pipeline_optimizer = PipelineOptimizer()
        
        # Initialize models
        self.models = {
            'lm_studio': LMStudioClient(),
            'ollama': OllamaClient(),
            'jan': JanClient()
        }
        
        # Initialize tools
        self.tools = {
            'tgpt': TGPTExecutor(),
            'interpreter': InterpreterManager()
        }
        
        # Capability mapping
        self.capability_mapping = self._initialize_capabilities()
        
        # Execution state
        self.active_tasks: Set[str] = set()
        self.task_history = []
        self.error_counts = {}
        
        # Performance tracking
        self.metrics = {
            'tasks_processed': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'total_duration': 0.0
        }

    def _initialize_capabilities(self) -> Dict[str, List[str]]:
        """Initialize system capabilities mapping"""
        return {
            # Model capabilities
            'code_generation': ['lm_studio:codestral-22b', 'ollama:codellama', 'jan:janai-large'],
            'pattern_analysis': ['lm_studio:deepthink-reasoning', 'jan:janai-reasoning'],
            'architecture': ['lm_studio:qwen2.5-coder', 'jan:janai-architect'],
            'vision': ['lm_studio:llama-3.2-11b-vision', 'jan:janai-vision'],
            
            # Tool capabilities
            'shell_execution': ['tgpt'],
            'code_execution': ['interpreter'],
            'pattern_recognition': ['interpreter', 'lm_studio:deepthink-reasoning'],
            'system_automation': ['tgpt', 'interpreter']
        }

    async def initialize(self) -> bool:
        """Initialize the orchestrator and all components"""
        try:
            self.logger.info("Initializing Integration Orchestrator")
            
            # Initialize core components
            await asyncio.gather(
                self.memory_manager.initialize(),
                self.execution_optimizer.initialize(),
                self.pipeline_optimizer.initialize()
            )
            
            # Initialize models
            model_inits = [
                model.initialize()
                for model in self.models.values()
            ]
            model_results = await asyncio.gather(*model_inits)
            if not all(model_results):
                raise RuntimeError("Model initialization failed")
            
            # Initialize tools
            tool_inits = [
                tool.initialize()
                for tool in self.tools.values()
            ]
            tool_results = await asyncio.gather(*tool_inits)
            if not all(tool_results):
                raise RuntimeError("Tool initialization failed")
            
            # Start monitoring
            asyncio.create_task(self._monitor_system())
            
            self.logger.info("Integration Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Orchestrator initialization failed: {e}")
            return False

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process task with optimal resource allocation and error handling"""
        task_id = task.get('id', str(datetime.now().timestamp()))
        start_time = datetime.now()
        
        try:
            # Validate task
            if not self._validate_task(task):
                raise ValueError("Invalid task configuration")
            
            # Optimize task execution
            optimized = await self.execution_optimizer.optimize(task)
            
            # Allocate memory
            if not await self.memory_manager.allocate(
                optimized.get('memory_requirements', {})
            ):
                raise MemoryError("Insufficient memory for task execution")
            
            # Select execution components
            components = await self._select_components(optimized)
            
            # Execute through pipeline
            result = await self.pipeline_optimizer.execute({
                **optimized,
                'components': components
            })
            
            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            await self._update_metrics(task_id, True, duration)
            
            return {
                'success': True,
                'result': result,
                'metrics': await self.get_metrics()
            }
            
        except Exception as e:
            self.logger.error(f"Task processing failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            await self._update_metrics(task_id, False, duration)
            return {
                'success': False,
                'error': str(e),
                'metrics': await self.get_metrics()
            }
        finally:
            # Release memory
            await self.memory_manager.release(
                task.get('memory_requirements', {})
            )

    async def _select_components(self, task: Dict[str, Any]) -> Dict[str, List[str]]:
        """Select optimal components for task execution"""
        selected = {
            'models': [],
            'tools': []
        }
        
        # Match capabilities to components
        for capability in task.get('capabilities', []):
            if capability in self.capability_mapping:
                components = self.capability_mapping[capability]
                for component in components:
                    if ':' in component:  # Model with specific configuration
                        selected['models'].append(component)
                    else:  # Tool
                        selected['tools'].append(component)
        
        # Order by performance metrics
        selected['models'] = await self._order_by_performance(
            selected['models'], 'model'
        )
        selected['tools'] = await self._order_by_performance(
            selected['tools'], 'tool'
        )
        
        return selected

    async def _order_by_performance(self, 
                                  components: List[str], 
                                  component_type: str) -> List[str]:
        """Order components by performance metrics"""
        scores = []
        
        for component in components:
            if component_type == 'model':
                model_name = component.split(':')[0]
                metrics = await self.models[model_name].get_metrics()
            else:
                metrics = await self.tools[component].get_metrics()
            
            # Calculate score based on success rate and latency
            success_rate = metrics.get('success_rate', 0)
            avg_duration = metrics.get('average_duration', float('inf'))
            score = success_rate / max(0.1, avg_duration)
            scores.append((component, score))
        
        # Sort by score descending
        return [c for c, _ in sorted(scores, key=lambda x: x[1], reverse=True)]

    def _validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate task configuration"""
        required_fields = ['capabilities']
        return all(field in task for field in required_fields)

    async def _update_metrics(self, 
                           task_id: str, 
                           success: bool, 
                           duration: float):
        """Update performance metrics"""
        self.metrics['tasks_processed'] += 1
        if success:
            self.metrics['successful_tasks'] += 1
        else:
            self.metrics['failed_tasks'] += 1
        self.metrics['total_duration'] += duration

    async def _monitor_system(self):
        """Monitor system health and performance"""
        while True:
            try:
                # Collect metrics
                model_metrics = await asyncio.gather(*[
                    model.get_metrics()
                    for model in self.models.values()
                ])
                tool_metrics = await asyncio.gather(*[
                    tool.get_metrics()
                    for tool in self.tools.values()
                ])
                
                # Check for issues
                await self._check_system_health(
                    model_metrics,
                    tool_metrics
                )
                
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(10)

    async def _check_system_health(self,
                                 model_metrics: List[Dict],
                                 tool_metrics: List[Dict]):
        """Check system health and handle issues"""
        issues = []
        
        # Check model health
        for i, metrics in enumerate(model_metrics):
            model = list(self.models.keys())[i]
            if metrics.get('error_rate', 0) > 0.2:  # 20% error rate threshold
                issues.append(f"High error rate for model {model}")
            if metrics.get('average_latency', 0) > 5.0:  # 5s latency threshold
                issues.append(f"High latency for model {model}")
        
        # Check tool health
        for i, metrics in enumerate(tool_metrics):
            tool = list(self.tools.keys())[i]
            if metrics.get('error_rate', 0) > 0.2:
                issues.append(f"High error rate for tool {tool}")
        
        # Handle issues
        if issues:
            self.logger.warning("System health issues detected:")
            for issue in issues:
                self.logger.warning(f"- {issue}")
            await self._handle_system_issues(issues)

    async def _handle_system_issues(self, issues: List[str]):
        """Handle detected system issues"""
        # Implement issue handling strategy
        # For now, just log the issues
        pass

    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        if self.metrics['tasks_processed'] == 0:
            return {
                **self.metrics,
                'success_rate': 1.0,
                'average_duration': 0.0,
                'component_metrics': {
                    'models': {},
                    'tools': {}
                }
            }
        
        # Calculate system metrics
        success_rate = (
            self.metrics['successful_tasks'] /
            self.metrics['tasks_processed']
        )
        avg_duration = (
            self.metrics['total_duration'] /
            self.metrics['tasks_processed']
        )
        
        # Collect component metrics
        model_metrics = {
            name: await model.get_metrics()
            for name, model in self.models.items()
        }
        tool_metrics = {
            name: await tool.get_metrics()
            for name, tool in self.tools.items()
        }
        
        return {
            **self.metrics,
            'success_rate': success_rate,
            'average_duration': avg_duration,
            'component_metrics': {
                'models': model_metrics,
                'tools': tool_metrics
            }
        }

    async def cleanup(self):
        """Cleanup system resources"""
        try:
            # Cleanup components
            await asyncio.gather(
                self.memory_manager.cleanup(),
                self.execution_optimizer.cleanup(),
                self.pipeline_optimizer.cleanup()
            )
            
            # Cleanup models
            await asyncio.gather(*[
                model.cleanup()
                for model in self.models.values()
            ])
            
            # Cleanup tools
            await asyncio.gather(*[
                tool.cleanup()
                for tool in self.tools.values()
            ])
            
            self.logger.info("System cleanup completed")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
            raise
