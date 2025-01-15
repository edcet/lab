import os
import sys
import platform
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class PlatformInfo:
    os_type: str
    architecture: str
    python_version: str
    available_memory: int
    cpu_count: int

class PlatformCompat:
    """Platform compatibility and environment detection layer"""

    def __init__(self):
        self._platform_info = self._detect_platform()
        self._config_cache = {}

    def _detect_platform(self) -> PlatformInfo:
        """Detect and return current platform information"""
        return PlatformInfo(
            os_type=platform.system().lower(),
            architecture=platform.machine(),
            python_version=platform.python_version(),
            available_memory=self._get_available_memory(),
            cpu_count=os.cpu_count() or 1
        )

    def _get_available_memory(self) -> int:
        """Cross-platform memory detection"""
        try:
            import psutil
            return psutil.virtual_memory().available
        except ImportError:
            return -1  # Unable to detect

    def get_platform_info(self) -> PlatformInfo:
        """Return current platform information"""
        return self._platform_info

    def load_platform_config(self, config_path: Optional[str] = None) -> Dict:
        """Load platform-specific configuration"""
        if config_path in self._config_cache:
            return self._config_cache[config_path]

        # ... existing config loading logic ...

        return self._config_cache[config_path]

    def is_supported_platform(self) -> bool:
        """Check if current platform is supported"""
        supported_platforms = {
            'linux', 'darwin', 'win32'
        }
        return sys.platform in supported_platforms

    def get_platform_specific_path(self, base_path: str) -> str:
        """Convert path to platform-specific format"""
        return os.path.normpath(base_path)

# ... existing code ...
