"""Neural Fabric Extended (NFX) Process Orchestrator

Manages and coordinates neural processing operations.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple, Callable
import numpy as np

@dataclass
class ProcessConfig:
    """Process configuration"""
    name: str
    priority: int
    resources: Dict[str, int]
    timeout: float

@dataclass
class ProcessStats:
    """Process statistics"""
    active: int
    completed: int
    failed: int
    avg_duration: float
    resource_usage: Dict[str, float]

class ProcessNode:
    """Individual process node"""

    def __init__(self, config: ProcessConfig):
        self.config = config
        self.stats = {
            'runs': 0,
            'failures': 0,
            'total_time': 0.0
        }
        self.status = 'idle'
        self._lock = asyncio.Lock()

    async def execute(self, data: np.ndarray) -> Optional[np.ndarray]:
        """Execute process on data"""
        async with self._lock:
            try:
                self.status = 'running'
                start_time = asyncio.get_event_loop().time()

                # Process implementation
                result = await self._process(data)

                # Update stats
                duration = asyncio.get_event_loop().time() - start_time
                self.stats['runs'] += 1
                self.stats['total_time'] += duration

                self.status = 'idle'
                return result

            except Exception as e:
                self.stats['failures'] += 1
                self.status = 'failed'
                logging.error(f"Process {self.config.name} failed: {e}")
                return None

    async def _process(self, data: np.ndarray) -> np.ndarray:
        """Process implementation"""
        # Override in subclasses
        return data

class ProcessGraph:
    """Process execution graph"""

    def __init__(self):
        self.nodes: Dict[str, ProcessNode] = {}
        self.edges: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()

    async def add_node(self, node: ProcessNode):
        """Add process node"""
        async with self._lock:
            self.nodes[node.config.name] = node
            self.edges[node.config.name] = []

    async def add_edge(self, from_node: str, to_node: str):
        """Add edge between nodes"""
        async with self._lock:
            if from_node in self.edges and to_node in self.nodes:
                self.edges[from_node].append(to_node)

    async def execute(self, data: np.ndarray) -> Dict[str, np.ndarray]:
        """Execute process graph"""
        results = {}
        visited = set()

        async def process_node(name: str, input_data: np.ndarray):
            if name in visited:
                return

            visited.add(name)
            node = self.nodes[name]

            # Process node
            result = await node.execute(input_data)
            results[name] = result

            # Process children
            for child in self.edges[name]:
                await process_node(child, result)

        # Start processing from root nodes (nodes with no incoming edges)
        root_nodes = self._find_root_nodes()
        for node in root_nodes:
            await process_node(node, data)

        return results

    def _find_root_nodes(self) -> List[str]:
        """Find nodes with no incoming edges"""
        incoming_edges = {node: 0 for node in self.nodes}

        for edges in self.edges.values():
            for target in edges:
                incoming_edges[target] += 1

        return [node for node, count in incoming_edges.items() if count == 0]

class Orchestrator:
    """Process orchestration and management"""

    def __init__(self):
        self.logger = logging.getLogger('nfx.process')
        self.graph = ProcessGraph()
        self._lock = asyncio.Lock()

    async def register_process(self, config: ProcessConfig,
                             processor: Optional[Callable] = None):
        """Register new process"""
        try:
            # Create process node
            if processor:
                node = CustomProcessNode(config, processor)
            else:
                node = ProcessNode(config)

            await self.graph.add_node(node)

        except Exception as e:
            self.logger.error(f"Failed to register process: {e}")
            raise

    async def connect_processes(self, from_process: str, to_process: str):
        """Connect processes in execution graph"""
        try:
            await self.graph.add_edge(from_process, to_process)
        except Exception as e:
            self.logger.error(f"Failed to connect processes: {e}")
            raise

    async def process(self, data: np.ndarray) -> Dict[str, np.ndarray]:
        """Process data through execution graph"""
        try:
            return await self.graph.execute(data)
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            raise

    def get_stats(self) -> Dict[str, ProcessStats]:
        """Get processing statistics"""
        stats = {}
        for name, node in self.graph.nodes.items():
            stats[name] = ProcessStats(
                active=1 if node.status == 'running' else 0,
                completed=node.stats['runs'],
                failed=node.stats['failures'],
                avg_duration=node.stats['total_time'] / max(node.stats['runs'], 1),
                resource_usage={}  # Implement resource tracking
            )
        return stats

class CustomProcessNode(ProcessNode):
    """Process node with custom processor"""

    def __init__(self, config: ProcessConfig,
                 processor: Callable[[np.ndarray], np.ndarray]):
        super().__init__(config)
        self.processor = processor

    async def _process(self, data: np.ndarray) -> np.ndarray:
        """Execute custom processor"""
        return self.processor(data)
