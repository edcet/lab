"""Unified Safety and Security System

This module implements a comprehensive safety and security system that consolidates:
- Input validation and sanitization
- Resource access control
- Rate limiting and circuit breaking
- Security policy enforcement
- Threat detection and prevention
- Audit logging
- State transition monitoring
- Critical operation protection
"""

import asyncio
from typing import Dict, List, Set, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import time
import json
import logging
import re
from pathlib import Path
import hashlib
import hmac
from cryptography.fernet import Fernet
from contextlib import asynccontextmanager
import aiofiles
import psutil
import signal
import sys
import traceback
import zlib
import msgpack

logger = logging.getLogger("security.safety")

@dataclass
class SecurityPolicy:
    """Security policy configuration"""
    max_tokens: int = 2000
    max_requests_per_minute: int = 60
    max_concurrent_requests: int = 10
    max_response_time: float = 30.0
    allowed_models: Set[str] = field(default_factory=set)
    blocked_patterns: Set[str] = field(default_factory=set)
    required_capabilities: Set[str] = field(default_factory=set)
    critical_operations: Set[str] = field(default_factory=lambda: {
        "state_transition",
        "shutdown",
        "initialization"
    })
    # Aggressive security thresholds
    max_memory_percent: float = 85.0
    max_cpu_percent: float = 80.0
    max_disk_percent: float = 90.0
    max_error_rate: float = 0.1
    max_suspicious_changes: int = 3
    max_concurrent_critical_ops: int = 5
    checksum_algorithm: str = "sha256"
    encryption_key_rotation_hours: int = 24
    audit_retention_days: int = 30

@dataclass
class SecurityContext:
    """Security context for request validation"""
    request_id: str
    timestamp: datetime
    source: str
    user: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    critical: bool = False
    checksum: Optional[str] = None
    parent_operation: Optional[str] = None
    resource_limits: Dict[str, float] = field(default_factory=dict)
    validation_chain: List[str] = field(default_factory=list)

@dataclass
class SecurityMetrics:
    """Security monitoring metrics"""
    request_count: int = 0
    critical_ops_count: int = 0
    blocked_attempts: int = 0
    state_transitions: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    last_incident: Optional[datetime] = None
    last_critical_op: Optional[datetime] = None
    suspicious_patterns: List[str] = field(default_factory=list)
    resource_violations: Dict[str, int] = field(default_factory=dict)
    validation_failures: Dict[str, int] = field(default_factory=dict)
    concurrent_ops_peak: int = 0

class SafetySystem:
    """Core safety and security system"""

    def __init__(self, config_path: Optional[Path] = None):
        # Core components
        self.policy = SecurityPolicy()
        self.metrics = SecurityMetrics()

        # State monitoring
        self._state_monitors: Dict[str, Callable] = {}
        self._critical_ops_lock = asyncio.Lock()
        self._operation_contexts: Dict[str, SecurityContext] = {}

        # Rate limiting
        self._request_counts: Dict[str, List[float]] = {}
        self._circuit_states: Dict[str, bool] = {}

        # Encryption and security
        self._setup_encryption()
        self._last_key_rotation = datetime.now()
        self._suspicious_ips: Set[str] = set()
        self._blocked_ips: Set[str] = set()
        self._validation_chain: List[Dict[str, Any]] = []

        # Resource monitoring
        self._resource_monitor = ResourceMonitor()

        # Load configuration if provided
        if config_path:
        self._load_config(config_path)

        # Start monitoring and maintenance
        self._start_background_tasks()

    def _setup_encryption(self):
        """Setup encryption with key rotation"""
        self._encryption_keys = []
        self._current_key_index = 0
        self._rotate_encryption_key()

    def _rotate_encryption_key(self):
        """Rotate encryption keys"""
        new_key = Fernet.generate_key()
        self._encryption_keys.append(Fernet(new_key))
        if len(self._encryption_keys) > 3:  # Keep last 3 keys
            self._encryption_keys.pop(0)
        self._current_key_index = len(self._encryption_keys) - 1
        self._last_key_rotation = datetime.now()

    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        self._tasks = [
            asyncio.create_task(self._monitor_security()),
            asyncio.create_task(self._cleanup_audit_logs()),
            asyncio.create_task(self._rotate_keys_periodically()),
            asyncio.create_task(self._monitor_resources()),
            asyncio.create_task(self._scan_suspicious_patterns())
        ]

    async def _cleanup_audit_logs(self):
        """Cleanup old audit logs"""
        while True:
            try:
                retention = timedelta(days=self.policy.audit_retention_days)
                cutoff = datetime.now() - retention

                async with aiofiles.open("audit.log", "r") as f:
                    lines = await f.readlines()

                # Keep only recent logs
                recent_logs = []
                for line in lines:
                    try:
                        log = self._decrypt_with_any_key(line.strip())
                        log_data = json.loads(log)
                        if datetime.fromisoformat(log_data["timestamp"]) > cutoff:
                            recent_logs.append(line)
                    except Exception as e:
                        logger.error(f"Error processing audit log: {e}")

                # Write back recent logs
                async with aiofiles.open("audit.log", "w") as f:
                    await f.writelines(recent_logs)

                await asyncio.sleep(3600)  # Check every hour

            except Exception as e:
                logger.error(f"Audit cleanup error: {e}")
                await asyncio.sleep(300)

    async def _rotate_keys_periodically(self):
        """Periodically rotate encryption keys"""
        while True:
            try:
                hours_since_rotation = (datetime.now() - self._last_key_rotation).total_seconds() / 3600
                if hours_since_rotation >= self.policy.encryption_key_rotation_hours:
                    self._rotate_encryption_key()
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                logger.error(f"Key rotation error: {e}")
                await asyncio.sleep(300)

    async def _monitor_resources(self):
        """Monitor system resources"""
        while True:
            try:
                metrics = await self._resource_monitor.get_metrics()

                # Check against thresholds
                violations = []
                if metrics.memory_percent > self.policy.max_memory_percent:
                    violations.append("memory")
                if metrics.cpu_percent > self.policy.max_cpu_percent:
                    violations.append("cpu")
                if metrics.disk_percent > self.policy.max_disk_percent:
                    violations.append("disk")

                if violations:
                    logger.warning(f"Resource violations detected: {violations}")
                    self.metrics.resource_violations.update({v: self.metrics.resource_violations.get(v, 0) + 1 for v in violations})

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(5)

    async def _scan_suspicious_patterns(self):
        """Scan for suspicious patterns"""
        while True:
            try:
                # Analyze recent operations
                suspicious = []
                async with self._critical_ops_lock:
                    for op_id, context in self._operation_contexts.items():
                        if await self._is_suspicious(context):
                            suspicious.append(op_id)

                if suspicious:
                    logger.warning(f"Suspicious operations detected: {suspicious}")
                    self.metrics.suspicious_patterns.extend(suspicious)

                await asyncio.sleep(30)  # Scan every 30 seconds

            except Exception as e:
                logger.error(f"Pattern scanning error: {e}")
                await asyncio.sleep(5)

    async def _is_suspicious(self, context: SecurityContext) -> bool:
        """Check if operation context is suspicious"""
        try:
            # Verify checksum
            if context.checksum and not self._verify_checksum(context):
                return True

            # Check resource usage
            if any(usage > limit for resource, (usage, limit) in
                  self._resource_monitor.get_usage_vs_limits(context.resource_limits).items()):
                return True

            # Verify validation chain
            if not self._verify_validation_chain(context.validation_chain):
                return True

            # Check for suspicious patterns in metadata
            if self._has_suspicious_patterns(context.metadata):
                return True

            return False

        except Exception as e:
            logger.error(f"Suspicious check error: {e}")
            return True

    def _verify_checksum(self, context: SecurityContext) -> bool:
        """Verify context checksum"""
        try:
            data = f"{context.request_id}:{context.timestamp.isoformat()}:{context.source}"
            if context.user:
                data += f":{context.user}"
            calculated = hashlib.new(self.policy.checksum_algorithm, data.encode()).hexdigest()
            return hmac.compare_digest(calculated, context.checksum or "")
        except Exception:
            return False

    def _verify_validation_chain(self, chain: List[str]) -> bool:
        """Verify validation chain integrity"""
        try:
            if not chain:
                return False

            # Verify chain sequence
            for i in range(1, len(chain)):
                prev_hash = hashlib.sha256(chain[i-1].encode()).hexdigest()
                if not chain[i].startswith(prev_hash[:8]):
                    return False

            return True

        except Exception:
            return False

    def _has_suspicious_patterns(self, metadata: Dict) -> bool:
        """Check for suspicious patterns in metadata"""
        try:
            patterns = [
                r"(?i)(exec|eval|system|subprocess)",
                r"(?i)(\/dev\/|\/proc\/|\/sys\/)",
                r"(?i)(\\x[0-9a-f]{2}){4,}",
                r"(?i)(base64|hex|rot13)",
            ]

            metadata_str = json.dumps(metadata)
            return any(re.search(pattern, metadata_str) for pattern in patterns)

        except Exception:
            return True

    @asynccontextmanager
    async def critical_operation(self, operation_id: str, context: SecurityContext):
        """Context manager for critical operations with exhaustive validation"""
        if not self._validate_operation_request(operation_id, context):
            raise SecurityError(f"Invalid operation request: {operation_id}")

        context.critical = True
        context.checksum = self._generate_context_checksum(context)
        self.metrics.critical_ops_count += 1
        self.metrics.last_critical_op = datetime.now()

        # Update concurrent operations peak
        async with self._critical_ops_lock:
            current_concurrent = len(self._operation_contexts)
            self.metrics.concurrent_ops_peak = max(
                self.metrics.concurrent_ops_peak,
                current_concurrent + 1
            )

            if current_concurrent >= self.policy.max_concurrent_critical_ops:
                raise SecurityError("Too many concurrent critical operations")

            # Record operation start
            self._operation_contexts[operation_id] = context
            await self._audit_critical_operation("start", operation_id, context)

        try:
            logger.info(f"Starting critical operation: {operation_id}")
            yield

        except Exception as e:
            logger.error(f"Critical operation error: {operation_id} - {e}")
            await self._audit_critical_operation("error", operation_id, context, error=str(e))
            raise

        finally:
            async with self._critical_ops_lock:
                if operation_id in self._operation_contexts:
                    del self._operation_contexts[operation_id]
                    await self._audit_critical_operation("complete", operation_id, context)
            logger.info(f"Completed critical operation: {operation_id}")

    def _validate_operation_request(self, operation_id: str, context: SecurityContext) -> bool:
        """Validate critical operation request"""
        try:
            # Validate operation ID format
            if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", operation_id):
                return False

            # Validate context
            if not self._validate_context(context):
                return False

            # Check if operation is allowed
            if not self._is_operation_allowed(operation_id, context):
                return False

            # Validate resource limits
            if not self._validate_resource_limits(context.resource_limits):
                return False

            return True

        except Exception:
            return False

    def _validate_context(self, context: SecurityContext) -> bool:
        """Validate security context"""
        try:
            # Basic validation
            if not context.request_id or not context.source:
                return False

            # Timestamp validation
            time_diff = abs((datetime.now() - context.timestamp).total_seconds())
            if time_diff > 300:  # 5 minutes max difference
                return False

            # Metadata validation
            if not self._validate_metadata(context.metadata):
                return False

            # Parent operation validation
            if context.parent_operation and not self._validate_parent_operation(context.parent_operation):
                return False

            return True

        except Exception:
            return False

    def _validate_metadata(self, metadata: Dict) -> bool:
        """Validate context metadata"""
        try:
            # Check size
            metadata_size = len(json.dumps(metadata))
            if metadata_size > 10000:  # 10KB limit
                return False

            # Check depth
            if self._get_dict_depth(metadata) > 5:
                return False

            # Check for invalid types
            if not self._validate_dict_types(metadata):
                return False

            return True

        except Exception:
            return False

    def _get_dict_depth(self, d: Dict, current_depth: int = 0) -> int:
        """Get dictionary nesting depth"""
        if not isinstance(d, dict) or current_depth > 20:
            return current_depth
        if not d:
            return current_depth + 1
        return max(self._get_dict_depth(v, current_depth + 1) for v in d.values())

    def _validate_dict_types(self, d: Dict) -> bool:
        """Validate dictionary value types"""
        valid_types = (str, int, float, bool, type(None))
        for k, v in d.items():
            if not isinstance(k, str):
                return False
            if isinstance(v, dict):
                if not self._validate_dict_types(v):
                    return False
            elif isinstance(v, (list, tuple)):
                if not all(isinstance(x, valid_types) for x in v):
                    return False
            elif not isinstance(v, valid_types):
                return False
        return True

    def _validate_parent_operation(self, op_id: str) -> bool:
        """Validate parent operation"""
        return op_id in self._operation_contexts

    def _validate_resource_limits(self, limits: Dict[str, float]) -> bool:
        """Validate resource limits"""
        try:
            valid_resources = {"cpu_percent", "memory_percent", "disk_percent"}

            # Check keys
            if not all(k in valid_resources for k in limits):
                return False

            # Check values
            if not all(isinstance(v, (int, float)) and 0 <= v <= 100 for v in limits.values()):
                return False

            # Check against policy
            if any(limits.get(k, 0) > getattr(self.policy, f"max_{k}") for k in valid_resources):
                return False

            return True

        except Exception:
            return False

    def _is_operation_allowed(self, operation_id: str, context: SecurityContext) -> bool:
        """Check if operation is allowed"""
        try:
            # Check if operation type is allowed
            op_type = operation_id.split("_")[0]
            if op_type not in self.policy.critical_operations:
                return False

            # Check source restrictions
            if context.source in self._blocked_ips:
                return False

            # Check user restrictions
            if context.user and not self._is_user_allowed(context.user, op_type):
                return False

            return True

        except Exception:
            return False

    def _is_user_allowed(self, user: str, operation_type: str) -> bool:
        """Check if user is allowed to perform operation"""
        # Implement user permission checking
        return True  # Placeholder

    async def _audit_critical_operation(self, event: str, operation_id: str, context: SecurityContext, **kwargs):
        """Audit critical operation events"""
        try:
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": f"critical_operation_{event}",
                "operation_id": operation_id,
                "request_id": context.request_id,
                "source": context.source,
                "user": context.user,
                "metadata": context.metadata,
                "resource_limits": context.resource_limits,
                **kwargs
            }

            # Add system metrics
            metrics = await self._resource_monitor.get_metrics()
            audit_entry["system_metrics"] = asdict(metrics)

            # Encrypt and compress
            encrypted_entry = self._encrypt_and_compress(audit_entry)

            # Write to audit log
            async with aiofiles.open("audit.log", "ab") as f:
                await f.write(encrypted_entry + b"\n")

        except Exception as e:
            logger.error(f"Audit logging error: {e}")

    def _encrypt_and_compress(self, data: Any) -> bytes:
        """Encrypt and compress data"""
        try:
            # Convert to bytes
            serialized = msgpack.packb(data)

            # Compress
            compressed = zlib.compress(serialized)

            # Encrypt with current key
            encrypted = self._encryption_keys[self._current_key_index].encrypt(compressed)

            return encrypted

        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def _decrypt_with_any_key(self, encrypted_data: bytes) -> Any:
        """Attempt to decrypt data with any available key"""
        last_error = None
        for key in reversed(self._encryption_keys):
            try:
                # Decrypt
                decrypted = key.decrypt(encrypted_data)

                # Decompress
                decompressed = zlib.decompress(decrypted)

                # Deserialize
                return msgpack.unpackb(decompressed)

            except Exception as e:
                last_error = e
                continue

        raise last_error

    def _generate_context_checksum(self, context: SecurityContext) -> str:
        """Generate context checksum"""
        try:
            # Combine context data
            data = [
                context.request_id,
                context.timestamp.isoformat(),
                context.source,
                context.user or "",
                json.dumps(context.metadata, sort_keys=True),
                json.dumps(context.resource_limits, sort_keys=True)
            ]

            # Calculate checksum
            return hashlib.new(
                self.policy.checksum_algorithm,
                ":".join(data).encode()
            ).hexdigest()

        except Exception as e:
            logger.error(f"Checksum generation error: {e}")
            return ""

class SecurityError(Exception):
    """Security-related error"""
    pass

@dataclass
class ResourceMetrics:
    """System resource metrics"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

class ResourceMonitor:
    """Monitor system resources"""

    def __init__(self):
        self.metrics_history: List[ResourceMetrics] = []
        self.max_history = 1000

    async def get_metrics(self) -> ResourceMetrics:
        """Get current resource metrics"""
        try:
            metrics = ResourceMetrics(
                cpu_percent=psutil.cpu_percent(),
                memory_percent=psutil.virtual_memory().percent,
                disk_percent=psutil.disk_usage('/').percent
            )

            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)

            return metrics

        except Exception as e:
            logger.error(f"Resource metrics error: {e}")
            return ResourceMetrics()

    def get_usage_vs_limits(self, limits: Dict[str, float]) -> Dict[str, Tuple[float, float]]:
        """Get current usage versus limits"""
        try:
            if not self.metrics_history:
                return {}

            current = self.metrics_history[-1]
            return {
                "cpu_percent": (current.cpu_percent, limits.get("cpu_percent", 100)),
                "memory_percent": (current.memory_percent, limits.get("memory_percent", 100)),
                "disk_percent": (current.disk_percent, limits.get("disk_percent", 100))
            }

        except Exception as e:
            logger.error(f"Usage comparison error: {e}")
            return {}
