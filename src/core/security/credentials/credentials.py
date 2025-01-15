"""Secure Credentials Management System"""

import asyncio
import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Any
import sqlite3

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

@dataclass
class CredentialConfig:
    """Configuration for credential management"""
    rotation_interval: int = 7  # days
    max_failed_attempts: int = 5
    lockout_duration: int = 30  # minutes
    key_derivation_iterations: int = 100000
    encryption_algorithm: str = "AES-256-GCM"

@dataclass
class AccessAttempt:
    """Tracks access attempts"""
    timestamp: datetime
    success: bool
    ip_address: str
    user_agent: str

class CredentialManager:
    """Secure credential management system"""

    def __init__(self, config_path: str = "~/.config/credentials"):
        self.config_path = Path(config_path).expanduser()
        self.config_path.mkdir(parents=True, exist_ok=True)

        # Initialize database and encryption
        self.db_path = self.config_path / "credentials.db"
        self._setup_database()

        # Load or generate master key
        self.master_key = self._load_or_generate_master_key()

        # Initialize Fernet for encryption
        self.fernet = Fernet(base64.urlsafe_b64encode(self.master_key))

        # Access tracking
        self.access_attempts: Dict[str, List[AccessAttempt]] = {}

        # Start background tasks
        self.background_tasks = set()
        self._start_background_tasks()

    def _setup_database(self):
        """Initialize the SQLite database with secure schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS credentials (
                    id TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    encrypted_data BLOB NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    rotation_due TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    credential_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    success BOOLEAN NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (credential_id) REFERENCES credentials(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS encryption_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_data BLOB NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    active BOOLEAN NOT NULL,
                    retired_at TIMESTAMP
                )
            """)

    def _load_or_generate_master_key(self) -> bytes:
        """Load existing master key or generate a new one"""
        key_path = self.config_path / "master.key"

        if key_path.exists():
            with open(key_path, "rb") as f:
                return f.read()

        # Generate new key
        key = os.urandom(32)  # 256-bit key

        # Save key securely
        with open(key_path, "wb") as f:
            f.write(key)

        return key

    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        loop = asyncio.get_event_loop()
        self.background_tasks.add(
            loop.create_task(self._key_rotation_loop())
        )
        self.background_tasks.add(
            loop.create_task(self._cleanup_loop())
        )

    async def _key_rotation_loop(self):
        """Periodically rotate encryption keys"""
        while True:
            try:
                # Check for credentials needing rotation
                await self._rotate_due_credentials()

                # Sleep until next check
                await asyncio.sleep(3600)  # Check hourly
            except Exception as e:
                print(f"Key rotation error: {e}")
                await asyncio.sleep(300)  # Back off on error

    async def _cleanup_loop(self):
        """Clean up old access logs and expired credentials"""
        while True:
            try:
                # Clean up old access logs
                self._cleanup_access_logs()

                # Clean up expired credentials
                await self._cleanup_expired_credentials()

                # Sleep until next cleanup
                await asyncio.sleep(86400)  # Run daily
            except Exception as e:
                print(f"Cleanup error: {e}")
                await asyncio.sleep(3600)  # Back off on error

    async def store_credential(
        self, service: str, credential_data: Dict[str, Any], credential_id: Optional[str] = None
    ) -> str:
        """Store encrypted credentials"""
        # Generate ID if not provided
        if credential_id is None:
            credential_id = base64.urlsafe_b64encode(os.urandom(16)).decode()

        # Encrypt credential data
        encrypted_data = self.fernet.encrypt(json.dumps(credential_data).encode())

        # Calculate rotation due date
        now = datetime.now()
        rotation_due = now + timedelta(days=7)  # Default 7-day rotation

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO credentials
                (id, service, encrypted_data, created_at, updated_at, rotation_due, access_count)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (credential_id, service, encrypted_data, now, now, rotation_due))

        return credential_id

    async def get_credential(
        self, credential_id: str, context: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt credentials with access tracking"""
        # Track access attempt
        attempt = AccessAttempt(
            timestamp=datetime.now(),
            success=False,
            ip_address=context.get("ip_address", "unknown"),
            user_agent=context.get("user_agent", "unknown")
        )

        # Check for lockout
        if self._is_locked_out(credential_id, context):
            self._log_access_attempt(credential_id, attempt)
            raise ValueError("Account is temporarily locked")

        try:
            # Retrieve encrypted data
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT encrypted_data FROM credentials WHERE id = ?",
                    (credential_id,)
                )
                result = cursor.fetchone()

                if not result:
                    return None

                # Decrypt data
                decrypted_data = self.fernet.decrypt(result[0])
                credential_data = json.loads(decrypted_data)

                # Update access count
                conn.execute(
                    "UPDATE credentials SET access_count = access_count + 1 WHERE id = ?",
                    (credential_id,)
                )

                # Log successful access
                attempt.success = True
                self._log_access_attempt(credential_id, attempt)

                return credential_data

        except Exception as e:
            # Log failed access
            self._log_access_attempt(credential_id, attempt)
            raise ValueError(f"Failed to retrieve credential: {e}")

    def _is_locked_out(self, credential_id: str, context: Dict[str, str]) -> bool:
        """Check if access should be locked out due to failed attempts"""
        recent_attempts = self.access_attempts.get(credential_id, [])
        if not recent_attempts:
            return False

        # Get recent failed attempts from same IP
        lockout_start = datetime.now() - timedelta(minutes=30)
        failed_attempts = [
            a for a in recent_attempts
            if not a.success
            and a.timestamp >= lockout_start
            and a.ip_address == context.get("ip_address")
        ]

        return len(failed_attempts) >= 5

    def _log_access_attempt(self, credential_id: str, attempt: AccessAttempt):
        """Log an access attempt"""
        # Update in-memory tracking
        if credential_id not in self.access_attempts:
            self.access_attempts[credential_id] = []
        self.access_attempts[credential_id].append(attempt)

        # Persist to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO access_log
                (credential_id, timestamp, success, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            """, (
                credential_id,
                attempt.timestamp,
                attempt.success,
                attempt.ip_address,
                attempt.user_agent
            ))

    async def _rotate_due_credentials(self):
        """Rotate credentials that are due for rotation"""
        with sqlite3.connect(self.db_path) as conn:
            # Get credentials due for rotation
            cursor = conn.execute(
                "SELECT id, encrypted_data FROM credentials WHERE rotation_due <= ?",
                (datetime.now(),)
            )

            for credential_id, encrypted_data in cursor:
                try:
                    # Decrypt with old key
                    decrypted_data = self.fernet.decrypt(encrypted_data)
                    credential_data = json.loads(decrypted_data)

                    # Re-encrypt with new key
                    await self.store_credential(
                        credential_id=credential_id,
                        service=credential_data.get("service", "unknown"),
                        credential_data=credential_data
                    )
                except Exception as e:
                    print(f"Failed to rotate credential {credential_id}: {e}")

    def _cleanup_access_logs(self):
        """Clean up old access logs"""
        cleanup_before = datetime.now() - timedelta(days=30)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM access_log WHERE timestamp < ?",
                (cleanup_before,)
            )

    async def _cleanup_expired_credentials(self):
        """Clean up expired credentials"""
        # Implementation depends on business rules for credential expiration
        pass

    async def close(self):
        """Clean up resources"""
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.background_tasks, return_exceptions=True)

        # Clear sensitive data
        self.master_key = None
        self.fernet = None
        self.access_attempts.clear()
