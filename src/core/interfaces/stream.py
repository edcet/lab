"""Unified Streaming Interface

This module implements a comprehensive streaming interface that consolidates:
- Model response streaming
- Event streaming
- Websocket handling
- Stream transformations
- Error handling
- Backpressure management
"""

import asyncio
from typing import Dict, List, Set, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from enum import Enum
import aiohttp
from aiohttp import web
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger("interface.stream")

class StreamType(Enum):
    """Types of streams supported"""
    MODEL_RESPONSE = "model_response"
    SYSTEM_EVENT = "system_event"
    METRICS = "metrics"
    LOGS = "logs"
    CUSTOM = "custom"

@dataclass
class StreamConfig:
    """Stream configuration"""
    buffer_size: int = 1000
    batch_size: int = 100
    flush_interval: float = 0.1
    compression: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class StreamContext:
    """Stream context information"""
    stream_id: str
    stream_type: StreamType
    source: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

class StreamBuffer:
    """Circular buffer for stream data"""

    def __init__(self, max_size: int):
        self.max_size = max_size
        self.buffer: List[Any] = []
        self.head = 0
        self.tail = 0
        self.size = 0
        self._lock = asyncio.Lock()

    async def push(self, item: Any):
        """Push item to buffer"""
        async with self._lock:
            if self.size == self.max_size:
                # Buffer full, overwrite oldest
                self.head = (self.head + 1) % self.max_size
            else:
                self.size += 1

            self.buffer.append(item)
            self.tail = (self.tail + 1) % self.max_size

    async def pop(self) -> Optional[Any]:
        """Pop oldest item from buffer"""
        async with self._lock:
            if self.size == 0:
                return None

            item = self.buffer[self.head]
            self.head = (self.head + 1) % self.max_size
            self.size -= 1
            return item

    async def peek(self) -> Optional[Any]:
        """Peek at oldest item without removing"""
        async with self._lock:
            if self.size == 0:
                return None
            return self.buffer[self.head]

class StreamProcessor:
    """Stream data processor and transformer"""

    def __init__(self, config: StreamConfig):
        self.config = config
        self.transformers: Dict[StreamType, List[callable]] = {}

    def add_transformer(self, stream_type: StreamType, transformer: callable):
        """Add a transformer for a stream type"""
        if stream_type not in self.transformers:
            self.transformers[stream_type] = []
        self.transformers[stream_type].append(transformer)

    async def process(self, data: Any, context: StreamContext) -> Any:
        """Process data through transformation pipeline"""
        if context.stream_type not in self.transformers:
            return data

        result = data
        for transformer in self.transformers[context.stream_type]:
            try:
                result = await transformer(result)
            except Exception as e:
                logger.error(f"Transformer error: {e}")
                break

        return result

class StreamManager:
    """Unified streaming interface manager"""

    def __init__(self, config: StreamConfig):
        # Core components
        self.config = config
        self.processor = StreamProcessor(config)

        # Stream tracking
        self.active_streams: Dict[str, StreamContext] = {}
        self.stream_buffers: Dict[str, StreamBuffer] = {}

        # Websocket connections
        self.ws_connections: Dict[str, Set[web.WebSocketResponse]] = {}

        # Monitoring
        self._monitor_task = asyncio.create_task(self._monitor_streams())

    async def create_stream(self,
                          stream_type: StreamType,
                          source: str,
                          metadata: Dict = None) -> StreamContext:
        """Create a new stream"""
        try:
            # Generate stream ID
            stream_id = f"{stream_type.value}_{source}_{datetime.now().timestamp()}"

            # Create context
            context = StreamContext(
                stream_id=stream_id,
                stream_type=stream_type,
                source=source,
                metadata=metadata or {}
            )

            # Initialize tracking
            self.active_streams[stream_id] = context
            self.stream_buffers[stream_id] = StreamBuffer(self.config.buffer_size)
            self.ws_connections[stream_id] = set()

            logger.info(f"Created stream: {stream_id}")
            return context

        except Exception as e:
            logger.error(f"Failed to create stream: {e}")
            raise

    async def push_data(self, context: StreamContext, data: Any):
        """Push data to stream"""
        try:
            # Process data
            processed = await self.processor.process(data, context)

            # Add to buffer
            await self.stream_buffers[context.stream_id].push(processed)

            # Notify websocket clients
            await self._notify_ws_clients(context.stream_id, processed)

        except Exception as e:
            logger.error(f"Failed to push data: {e}")
            raise

    async def subscribe(self,
                       stream_id: str,
                       ws: web.WebSocketResponse):
        """Subscribe websocket to stream"""
        try:
            if stream_id not in self.active_streams:
                raise ValueError(f"Stream not found: {stream_id}")

            self.ws_connections[stream_id].add(ws)
            logger.info(f"Subscribed to stream: {stream_id}")

            try:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"Websocket error: {ws.exception()}")
                        break

            finally:
                self.ws_connections[stream_id].remove(ws)

        except Exception as e:
            logger.error(f"Subscription error: {e}")
            raise

    async def read_stream(self,
                         context: StreamContext,
                         batch_size: Optional[int] = None) -> AsyncGenerator[Any, None]:
        """Read data from stream"""
        try:
            buffer = self.stream_buffers[context.stream_id]
            batch = []

            while True:
                item = await buffer.pop()
                if item is None:
                    if batch:
                        yield batch
                        batch = []
                    await asyncio.sleep(self.config.flush_interval)
                    continue

                batch.append(item)
                if len(batch) >= (batch_size or self.config.batch_size):
                    yield batch
                    batch = []

        except Exception as e:
            logger.error(f"Stream read error: {e}")
            raise

    async def close_stream(self, stream_id: str):
        """Close stream and cleanup"""
        try:
            # Close websocket connections
            connections = self.ws_connections.get(stream_id, set())
            for ws in connections:
                await ws.close()

            # Cleanup
            self.active_streams.pop(stream_id, None)
            self.stream_buffers.pop(stream_id, None)
            self.ws_connections.pop(stream_id, None)

            logger.info(f"Closed stream: {stream_id}")

        except Exception as e:
            logger.error(f"Stream closure error: {e}")
            raise

    async def _monitor_streams(self):
        """Monitor active streams"""
        while True:
            try:
                for stream_id, context in list(self.active_streams.items()):
                    # Check stream health
                    buffer = self.stream_buffers[stream_id]
                    if buffer.size >= buffer.max_size * 0.9:  # 90% full
                        logger.warning(f"Stream buffer near capacity: {stream_id}")

                    # Check client connections
                    connections = self.ws_connections[stream_id]
                    if not connections:
                        logger.info(f"No active clients for stream: {stream_id}")

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Stream monitoring error: {e}")
                await asyncio.sleep(5)  # Back off on error

    async def _notify_ws_clients(self, stream_id: str, data: Any):
        """Notify websocket clients of new data"""
        message = json.dumps({
            "stream_id": stream_id,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })

        dead_connections = set()

        for ws in self.ws_connections[stream_id]:
            try:
                await ws.send_str(message)
            except ConnectionClosed:
                dead_connections.add(ws)
            except Exception as e:
                logger.error(f"Failed to notify client: {e}")
                dead_connections.add(ws)

        # Cleanup dead connections
        self.ws_connections[stream_id] -= dead_connections
