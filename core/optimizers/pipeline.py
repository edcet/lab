"""Pipeline optimization for efficient task processing"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass
import networkx as nx
from collections import defaultdict

@dataclass
class PipelineStats:
    """Pipeline performance statistics"""
    total_pipelines: int = 0
    completed_pipelines: int = 0
    failed_pipelines: int = 0
    total_duration: float = 0.0
    stage_metrics: Dict[str, Dict[str, float]] = None
    
    def __post_init__(self):
        self.stage_metrics = defaultdict(
            lambda: {
                'executions': 0,
                'total_duration': 0.0,
                'failures': 0
            }
        )

class PipelineOptimizer:
    """Optimizes task pipeline execution"""
    
    def __init__(self):
        self.stats = PipelineStats()
        self.logger = logging.getLogger(__name__)
        self.pipeline_cache = {}
        self.active_pipelines = set()
        self.pipeline_lock = asyncio.Lock()
        
        # Pipeline configuration
        self.max_concurrent = 8
        self.stage_timeout = 300  # 5 minutes per stage
        self.retry_limit = 3
        
        # Optimization parameters
        self.reorder_threshold = 0.8  # Stage success rate for reordering
        self.batch_size = 16
        self.adaptation_rate = 0.1

    async def initialize(self) -> bool:
        """Initialize pipeline optimizer"""
        try:
            # Initialize monitoring and optimization 
            asyncio.create_task(self._monitor_pipelines())
            asyncio.create_task(self._optimize_pipelines())
            return True
        except Exception as e:
            self.logger.error(f"Pipeline initialization failed: {e}")
            return False

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task through optimized pipeline"""
        pipeline_id = self._generate_pipeline_id(task)
        start_time = datetime.now()
        
        try:
            async with self.pipeline_lock:
                # Check concurrent pipeline limit
                if len(self.active_pipelines) >= self.max_concurrent:
                    await self._wait_for_pipeline()
                
                self.active_pipelines.add(pipeline_id)
            
            self.stats.total_pipelines += 1
            
            # Generate or get cached pipeline
            pipeline = await self._get_pipeline(task)
            
            # Execute pipeline stages
            result = await self._execute_pipeline(pipeline, task)
            
            # Update stats
            duration = (datetime.now() - start_time).total_seconds()
            await self._update_stats(pipeline_id, True, duration)
            
            return result

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            await self._update_stats(pipeline_id, False, duration)
            raise
        finally:
            self.active_pipelines.remove(pipeline_id)

    async def _wait_for_pipeline(self):
        """Wait for pipeline capacity"""
        while len(self.active_pipelines) >= self.max_concurrent:
            await asyncio.sleep(0.1)

    async def _update_stats(self, 
                        pipeline_id: str, 
                        success: bool, 
                        duration: float):
        """Update pipeline statistics"""
        if success:
            self.stats.completed_pipelines += 1
        else:
            self.stats.failed_pipelines += 1
        
        self.stats.total_duration += duration

    def _update_stage_metrics(self, 
                        stage_name: str, 
                        success: bool, 
                        duration: float):
        """Update stage-specific metrics"""
        metrics = self.stats.stage_metrics[stage_name]
        metrics['executions'] += 1
        if not success:
            metrics['failures'] += 1
        metrics['total_duration'] += duration

    async def _monitor_pipelines(self):
        """Monitor pipeline performance"""
        while True:
            try:
                # Calculate success rates and latencies
                metrics = await self.get_metrics()
                
                # Adjust concurrent pipeline limit
                if metrics['success_rate'] < 0.9:
                    self.max_concurrent = max(1, self.max_concurrent - 1)
                elif metrics['success_rate'] > 0.95:
                    self.max_concurrent = min(32, self.max_concurrent + 1)
                
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.error(f"Pipeline monitoring error: {e}")
                await asyncio.sleep(10)

    async def _optimize_pipelines(self):
        """Periodically optimize pipeline configurations"""
        while True:
            try:
                for task_type, pipeline in self.pipeline_cache.items():
                    # Analyze stage performance
                    stage_metrics = self._analyze_stage_performance(pipeline)
                    
                    # Reorder stages if needed
                    if self._should_reorder_stages(stage_metrics):
                        new_pipeline = self._reorder_pipeline_stages(
                            pipeline, 
                            stage_metrics
                        )
                        self.pipeline_cache[task_type] = new_pipeline
                
                await asyncio.sleep(60)  # Optimize every minute
            except Exception as e:
                self.logger.error(f"Pipeline optimization error: {e}")
                await asyncio.sleep(30)

    def _analyze_stage_performance(self, 
                            pipeline: List[Dict]) -> Dict[str, float]:
        """Analyze performance metrics for pipeline stages"""
        analysis = {}
        for stage in pipeline:
            metrics = self.stats.stage_metrics[stage['name']]
            if metrics['executions'] > 0:
                success_rate = 1 - (metrics['failures'] / metrics['executions'])
                avg_duration = (
                    metrics['total_duration'] / metrics['executions']
                )
                analysis[stage['name']] = {
                    'success_rate': success_rate,
                    'avg_duration': avg_duration
                }
        return analysis

    def _should_reorder_stages(self, 
                        stage_metrics: Dict[str, Dict]) -> bool:
        """Determine if pipeline stages should be reordered"""
        # Check for significant performance differences
        success_rates = [m['success_rate'] for m in stage_metrics.values()]
        durations = [m['avg_duration'] for m in stage_metrics.values()]
        
        return (
            max(success_rates) - min(success_rates) > 0.2 or
            max(durations) / min(durations) > 3
        )

    def _reorder_pipeline_stages(self, 
                            pipeline: List[Dict], 
                            metrics: Dict[str, Dict]) -> List[Dict]:
        """Reorder pipeline stages for optimal performance"""
        # Calculate stage scores (higher is better)
        stage_scores = {
            stage['name']: (
                metrics[stage['name']]['success_rate'] /
                max(0.1, metrics[stage['name']]['avg_duration'])
            )
            for stage in pipeline
            if stage['name'] in metrics
        }
        
        # Sort stages by score, keeping pre/post-processing in place
        preprocessors = [s for s in pipeline if s['type'] == 'preparation']
        postprocessors = [s for s in pipeline if s['type'] == 'finalization']
        main_stages = [
            s for s in pipeline 
            if s['type'] not in ['preparation', 'finalization']
        ]
        
        # Sort main stages by score
        sorted_main_stages = sorted(
            main_stages,
            key=lambda s: stage_scores.get(s['name'], 0),
            reverse=True
        )
        
        return preprocessors + sorted_main_stages + postprocessors

    async def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline performance metrics"""
        if self.stats.total_pipelines == 0:
            return {
                'total_pipelines': 0,
                'success_rate': 1.0,
                'average_duration': 0.0,
                'active_pipelines': len(self.active_pipelines),
                'stage_metrics': {}
            }
        
        success_rate = (
            self.stats.completed_pipelines / 
            self.stats.total_pipelines
        )
        avg_duration = (
            self.stats.total_duration / 
            self.stats.total_pipelines
        )
        
        return {
            'total_pipelines': self.stats.total_pipelines,
            'success_rate': success_rate,
            'average_duration': avg_duration,
            'active_pipelines': len(self.active_pipelines),
            'stage_metrics': {
                name: {
                    'success_rate': 1 - (metrics['failures'] / metrics['executions']),
                    'average_duration': (
                        metrics['total_duration'] / metrics['executions']
                    )
                }
                for name, metrics in self.stats.stage_metrics.items()
                if metrics['executions'] > 0
            }
        }

    async def cleanup(self):
        """Cleanup pipeline resources"""
        self.pipeline_cache.clear()
        self.active_pipelines.clear()

"""Pipeline optimization for efficient task processing"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass
import networkx as nx
from collections import defaultdict

@dataclass
class PipelineStats:
    """Pipeline performance statistics"""
    total_pipelines: int = 0
    completed_pipelines: int = 0
    failed_pipelines: int = 0
    total_duration: float = 0.0
    stage_metrics: Dict[str, Dict[str, float]] = None

    def __post_init__(self):
        self.stage_metrics = defaultdict(
            lambda: {
                'executions': 0,
                'total_duration': 0.0,
                'failures': 0
            }
        )

class PipelineOptimizer:
    """Optimizes task pipeline execution"""
    
    def __init__(self):
        self.stats = PipelineStats()
        self.logger = logging.getLogger(__name__)
        self.pipeline_cache = {}
        self.active_pipelines = set()
        self.pipeline_lock = asyncio.Lock()
        
        # Pipeline configuration
        self.max_concurrent = 8
        self.stage_timeout = 300  # 5 minutes per stage
        self.retry_limit = 3
        
        # Optimization parameters
        self.reorder_threshold = 0.8  # Stage success rate for reordering
        self.batch_size = 16
        self.adaptation_rate = 0.1

    async def initialize(self) -> bool:
        """Initialize pipeline optimizer"""
        try:
            # Initialize monitoring and optimization
            asyncio.create_task(self._monitor_pipelines())
            asyncio.create_task(self._optimize_pipelines())
            return True
        except Exception as e:
            self.logger.error(f"Pipeline initialization failed: {e}")
            return False

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task through optimized pipeline"""
        pipeline_id = self._generate_pipeline_id(task)
        start_time = datetime.now()
        
        try:
            async with self.pipeline_lock:
                # Check concurrent pipeline limit
                if len(self.active_pipelines) >= self.max_concurrent:
                    await self._wait_for_pipeline()
                
                self.active_pipelines.add(pipeline_id)
            
            self.stats.total_pipelines += 1
            
            # Generate or get cached pipeline
            pipeline = await self._get_pipeline(task)
            
            # Execute pipeline stages
            result = await self._execute_pipeline(pipeline, task)
            
            # Update stats
            duration = (datetime.now() - start_time).total_seconds()
            await self._update_stats(pipeline_id, True, duration)
            
            return result

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            await self._update_stats(pipeline_id, False, duration)
            raise
        finally:
            self.active_pipelines.remove(pipeline_id)

    async def _wait_for_pipeline(self):
        """Wait for pipeline capacity"""
        while len(self.active_pipelines) >= self.max_concurrent:
            await asyncio.sleep(0.1)

    async def _update_stats(self, 
                         pipeline_id: str, 
                         success: bool, 
                         duration: float):
        """Update pipeline statistics"""
        if success:
            self.stats.completed_pipelines += 1
        else:
            self.stats.failed_pipelines += 1
        
        self.stats.total_duration += duration

    def _update_stage_metrics(self, 
                           stage_name: str, 
                           success: bool, 
                           duration: float):
        """Update stage-specific metrics"""
        metrics = self.stats.stage_metrics[stage_name]
        metrics['executions'] += 1
        if not success:
            metrics['failures'] += 1
        metrics['total_duration'] += duration

    async def _monitor_pipelines(self):
        """Monitor pipeline performance"""
        while True:
            try:
                # Calculate success rates and latencies
                metrics = await self.get_metrics()
                
                # Adjust concurrent pipeline limit
                if metrics['success_rate'] < 0.9:
                    self.max_concurrent = max(1, self.max_concurrent - 1)
                elif metrics['success_rate'] > 0.95:
                    self.max_concurrent = min(32, self.max_concurrent + 1)
                
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.error(f"Pipeline monitoring error: {e}")
                await asyncio.sleep(10)

    async def _optimize_pipelines(self):
        """Periodically optimize pipeline configurations"""
        while True:
            try:
                for task_type, pipeline in self.pipeline_cache.items():
                    # Analyze stage performance
                    stage_metrics = self._analyze_stage_performance(pipeline)
                    
                    # Reorder stages if needed
                    if self._should_reorder_stages(stage_metrics):
                        new_pipeline = self._reorder_pipeline_stages(
                            pipeline, 
                            stage_metrics
                        )
                        self.pipeline_cache[task_type] = new_pipeline
                
                await asyncio.sleep(60)  # Optimize every minute
            except Exception as e:
                self.logger.error(f"Pipeline optimization error: {e}")
                await asyncio.sleep(30)

    def _analyze_stage_performance(self, 
                                pipeline: List[Dict]) -> Dict[str, float]:
        """Analyze performance metrics for pipeline stages"""
        analysis = {}
        for stage in pipeline:
            metrics = self.stats.stage_metrics[stage['name']]
            if metrics['executions'] > 0:
                success_rate = 1 - (metrics['failures'] / metrics['executions'])
                avg_duration = (
                    metrics['total_duration'] / metrics['executions']
                )
                analysis[stage['name']] = {
                    'success_rate': success_rate,
                    'avg_duration': avg_duration
                }
        return analysis

    def _should_reorder_stages(self, 
                            stage_metrics: Dict[str, Dict]) -> bool:
        """Determine if pipeline stages should be reordered"""
        # Check for significant performance differences
        success_rates = [m['success_rate'] for m in stage_metrics.values()]
        durations = [m['avg_duration'] for m in stage_metrics.values()]
        
        return (
            max(success_rates) - min(success_rates) > 0.2 or
            max(durations) / min(durations) > 3
        )

    def _reorder_pipeline_stages(self, 
                              pipeline: List[Dict], 
                              metrics: Dict[str, Dict]) -> List[Dict]:
        """Reorder pipeline stages for optimal performance"""
        # Calculate stage scores (higher is better)
        stage_scores = {
            stage['name']: (
                metrics[stage['name']]['success_rate'] /
                max(0.1, metrics[stage['name']]['avg_duration'])
            )
            for stage in pipeline
            if stage['name'] in metrics
        }
        
        # Sort stages by score, keeping pre/post-processing in place
        preprocessors = [s for s in pipeline if s['type'] == 'preparation']
        postprocessors = [s for s in pipeline if s['type'] == 'finalization']
        main_stages = [
            s for s in pipeline 
            if s['type'] not in ['preparation', 'finalization']
        ]
        
        # Sort main stages by score
        sorted_main_stages = sorted(
            main_stages,
            key=lambda s: stage_scores.get(s['name'], 0),
            reverse=True
        )
        
        return preprocessors + sorted_main_stages + postprocessors

    async def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline performance metrics"""
        if self.stats.total_pipelines == 0:
            return {
                'total_pipelines': 0,
                'success_rate': 1.0,
                'average_duration': 0.0,
                'active_pipelines': len(self.active_pipelines),
                'stage_metrics': {}
            }
        
        success_rate = (
            self.stats.completed_pipelines / 
            self.stats.total_pipelines
        )
        avg_duration = (
            self.stats.total_duration / 
            self.stats.total_pipelines
        )
        
        return {
            'total_pipelines': self.stats.total_pipelines,
            'success_rate': success_rate,
            'average_duration': avg_duration,
            'active_pipelines': len(self.active_pipelines),
            'stage_metrics': {
                name: {
                    'success_rate': 1 - (metrics['failures'] / metrics['executions']),
                    'average_duration': (
                        metrics['total_duration'] / metrics['executions']
                    )
                }
                for name, metrics in self.stats.stage_metrics.items()
                if metrics['executions'] > 0
            }
        }

    async def cleanup(self):
        """Cleanup pipeline resources"""
        self.pipeline_cache.clear()
        self.active_pipelines.clear()
