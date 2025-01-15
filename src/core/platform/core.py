"""Platform Compatibility Layer for Cross-Platform Operations"""

import asyncio
import os
import platform
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import psutil

class PlatformType(Enum):
    """Supported platform types"""
    LINUX = auto()
    MACOS = auto()
    WINDOWS = auto()
    UNKNOWN = auto()

@dataclass
class PlatformConfig:
    """Platform-specific configuration"""
    shell_path: str
    config_dir: str
    cache_dir: str
    data_dir: str
    temp_dir: str
    env_vars: Dict[str, str]
    path_separator: str
    line_ending: str
    encoding: str = "utf-8"

@dataclass
class SystemResources:
    """System resource information"""
    cpu_count: int
    memory_total: int
    memory_available: int
    disk_total: int
    disk_available: int
    network_interfaces: List[str]

class PlatformManager:
    """Core platform compatibility layer"""

    def __init__(self):
        # Detect platform
        self.platform_type = self._detect_platform()

        # Load platform-specific configuration
        self.config = self._load_platform_config()

        # Initialize paths
        self._setup_directories()

        # Cache system info
        self.system_info = self._get_system_info()

        # Track running processes
        self.managed_processes: Dict[int, subprocess.Popen] = {}

    def _detect_platform(self) -> PlatformType:
        """Detect current platform type"""
        system = platform.system().lower()

        if system == "linux":
            return PlatformType.LINUX
        elif system == "darwin":
            return PlatformType.MACOS
        elif system == "windows":
            return PlatformType.WINDOWS
        else:
            return PlatformType.UNKNOWN

    def _load_platform_config(self) -> PlatformConfig:
        """Load platform-specific configuration"""
        if self.platform_type == PlatformType.LINUX:
            return PlatformConfig(
                shell_path="/bin/bash",
                config_dir=os.path.expanduser("~/.config"),
                cache_dir=os.path.expanduser("~/.cache"),
                data_dir=os.path.expanduser("~/.local/share"),
                temp_dir="/tmp",
                env_vars={
                    "XDG_CONFIG_HOME": "~/.config",
                    "XDG_CACHE_HOME": "~/.cache",
                    "XDG_DATA_HOME": "~/.local/share"
                },
                path_separator="/",
                line_ending="\n"
            )

        elif self.platform_type == PlatformType.MACOS:
            return PlatformConfig(
                shell_path="/bin/zsh",
                config_dir=os.path.expanduser("~/Library/Application Support"),
                cache_dir=os.path.expanduser("~/Library/Caches"),
                data_dir=os.path.expanduser("~/Library/Application Support"),
                temp_dir="/tmp",
                env_vars={
                    "XDG_CONFIG_HOME": "~/Library/Application Support",
                    "XDG_CACHE_HOME": "~/Library/Caches",
                    "XDG_DATA_HOME": "~/Library/Application Support"
                },
                path_separator="/",
                line_ending="\n"
            )

        elif self.platform_type == PlatformType.WINDOWS:
            return PlatformConfig(
                shell_path="cmd.exe",
                config_dir=os.path.expandvars("%APPDATA%"),
                cache_dir=os.path.expandvars("%LOCALAPPDATA%"),
                data_dir=os.path.expandvars("%APPDATA%"),
                temp_dir=os.path.expandvars("%TEMP%"),
                env_vars={
                    "XDG_CONFIG_HOME": "%APPDATA%",
                    "XDG_CACHE_HOME": "%LOCALAPPDATA%",
                    "XDG_DATA_HOME": "%APPDATA%"
                },
                path_separator="\\",
                line_ending="\r\n"
            )

        else:
            raise RuntimeError(f"Unsupported platform: {platform.system()}")

    def _setup_directories(self):
        """Create necessary platform directories"""
        for dir_path in [
            self.config.config_dir,
            self.config.cache_dir,
            self.config.data_dir
        ]:
            os.makedirs(os.path.expanduser(dir_path), exist_ok=True)

    def _get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information"""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": sys.version,
            "python_implementation": platform.python_implementation()
        }

    async def get_system_resources(self) -> SystemResources:
        """Get current system resource information"""
        return SystemResources(
            cpu_count=os.cpu_count() or 1,
            memory_total=psutil.virtual_memory().total,
            memory_available=psutil.virtual_memory().available,
            disk_total=psutil.disk_usage('/').total,
            disk_available=psutil.disk_usage('/').free,
            network_interfaces=[
                iface for iface in psutil.net_if_addrs().keys()
            ]
        )

    def get_config_path(self, app_name: str) -> Path:
        """Get platform-specific config path for an application"""
        base_path = Path(os.path.expanduser(self.config.config_dir))
        return base_path / app_name

    def get_cache_path(self, app_name: str) -> Path:
        """Get platform-specific cache path for an application"""
        base_path = Path(os.path.expanduser(self.config.cache_dir))
        return base_path / app_name

    def get_data_path(self, app_name: str) -> Path:
        """Get platform-specific data path for an application"""
        base_path = Path(os.path.expanduser(self.config.data_dir))
        return base_path / app_name

    def get_temp_path(self, prefix: str = "") -> Path:
        """Get platform-specific temporary path"""
        return Path(self.config.temp_dir) / f"{prefix}{os.urandom(8).hex()}"

    async def execute_command(
        self,
        command: Union[str, List[str]],
        shell: bool = False,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute a command with platform-specific adjustments"""
        try:
            # Prepare command
            if isinstance(command, str) and not shell:
                command = command.split()

            # Prepare environment
            full_env = os.environ.copy()
            if env:
                full_env.update(env)

            # Execute command
            process = await asyncio.create_subprocess_exec(
                *command if not shell else command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=full_env,
                shell=shell
            )

            # Track process
            self.managed_processes[process.pid] = process

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                return {
                    "returncode": process.returncode,
                    "stdout": stdout.decode(self.config.encoding),
                    "stderr": stderr.decode(self.config.encoding),
                    "pid": process.pid
                }

            except asyncio.TimeoutError:
                process.terminate()
                raise TimeoutError(f"Command timed out after {timeout} seconds")

            finally:
                # Clean up process tracking
                self.managed_processes.pop(process.pid, None)

        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "pid": None
            }

    async def terminate_process(self, pid: int, force: bool = False):
        """Terminate a process with platform-specific handling"""
        try:
            process = psutil.Process(pid)

            if force:
                if self.platform_type == PlatformType.WINDOWS:
                    process.kill()
                else:
                    os.kill(pid, signal.SIGKILL)
            else:
                if self.platform_type == PlatformType.WINDOWS:
                    process.terminate()
                else:
                    os.kill(pid, signal.SIGTERM)

            # Wait for process to terminate
            try:
                await asyncio.wait_for(
                    self._wait_for_process_exit(pid),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                if not force:
                    # Retry with force
                    await self.terminate_process(pid, force=True)

        except psutil.NoSuchProcess:
            pass  # Process already terminated

        except Exception as e:
            print(f"Error terminating process {pid}: {e}")

    async def _wait_for_process_exit(self, pid: int):
        """Wait for a process to exit"""
        while True:
            try:
                process = psutil.Process(pid)
                if process.status() == psutil.STATUS_ZOMBIE:
                    break
                await asyncio.sleep(0.1)
            except psutil.NoSuchProcess:
                break

    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Normalize path for current platform"""
        return Path(path).expanduser().resolve()

    def convert_path_to_url(self, path: Union[str, Path]) -> str:
        """Convert file path to URL for current platform"""
        path = self.normalize_path(path)

        if self.platform_type == PlatformType.WINDOWS:
            return f"file:///{str(path).replace(os.sep, '/')}"
        else:
            return f"file://{path}"

    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Get detailed process information"""
        try:
            process = psutil.Process(pid)
            return {
                "pid": process.pid,
                "name": process.name(),
                "status": process.status(),
                "created": process.create_time(),
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "command": process.cmdline(),
                "cwd": process.cwd(),
                "username": process.username(),
                "nice": process.nice(),
                "num_threads": process.num_threads(),
                "memory_info": process.memory_info()._asdict()
            }
        except psutil.NoSuchProcess:
            return None

    def list_processes(self) -> List[Dict[str, Any]]:
        """List all running processes with details"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes

    def get_environment_variables(self) -> Dict[str, str]:
        """Get platform-specific environment variables"""
        env_vars = os.environ.copy()

        # Add platform-specific variables
        env_vars.update(self.config.env_vars)

        return env_vars

    def set_environment_variable(self, name: str, value: str, permanent: bool = False):
        """Set environment variable with platform-specific handling"""
        os.environ[name] = value

        if permanent:
            if self.platform_type == PlatformType.WINDOWS:
                subprocess.run(
                    ['setx', name, value],
                    capture_output=True,
                    text=True
                )
            else:
                # Add to shell rc file
                shell_rc = self._get_shell_rc_path()
                if shell_rc:
                    with open(shell_rc, 'a') as f:
                        f.write(f'\nexport {name}="{value}"\n')

    def _get_shell_rc_path(self) -> Optional[Path]:
        """Get path to shell rc file"""
        home = Path.home()

        if self.platform_type == PlatformType.LINUX:
            if os.environ.get('SHELL', '').endswith('bash'):
                return home / '.bashrc'
            elif os.environ.get('SHELL', '').endswith('zsh'):
                return home / '.zshrc'

        elif self.platform_type == PlatformType.MACOS:
            if os.environ.get('SHELL', '').endswith('bash'):
                return home / '.bash_profile'
            elif os.environ.get('SHELL', '').endswith('zsh'):
                return home / '.zshrc'

        return None

    def copy_file(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
        follow_symlinks: bool = True
    ):
        """Copy file with platform-specific handling"""
        src = self.normalize_path(src)
        dst = self.normalize_path(dst)

        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        try:
            shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
        except OSError as e:
            if self.platform_type == PlatformType.WINDOWS:
                # Retry with fallback method on Windows
                try:
                    with open(src, 'rb') as fsrc:
                        with open(dst, 'wb') as fdst:
                            shutil.copyfileobj(fsrc, fdst)
                except OSError:
                    raise e
            else:
                raise

    def move_file(
        self,
        src: Union[str, Path],
        dst: Union[str, Path]
    ):
        """Move file with platform-specific handling"""
        src = self.normalize_path(src)
        dst = self.normalize_path(dst)

        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        try:
            shutil.move(src, dst)
        except OSError as e:
            if self.platform_type == PlatformType.WINDOWS:
                # Retry with copy and delete on Windows
                try:
                    self.copy_file(src, dst)
                    os.unlink(src)
                except OSError:
                    raise e
            else:
                raise

    def create_symlink(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
        target_is_directory: bool = False
    ):
        """Create symlink with platform-specific handling"""
        src = self.normalize_path(src)
        dst = self.normalize_path(dst)

        try:
            os.symlink(src, dst, target_is_directory=target_is_directory)
        except OSError as e:
            if self.platform_type == PlatformType.WINDOWS:
                # Requires elevated privileges on Windows
                if not ctypes.windll.shell32.IsUserAnAdmin():
                    raise PermissionError(
                        "Creating symlinks on Windows requires administrator privileges"
                    ) from e
            raise

    def get_file_info(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Get detailed file information"""
        path = self.normalize_path(path)
        stat = path.stat()

        return {
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "accessed": datetime.fromtimestamp(stat.st_atime),
            "mode": stat.st_mode,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "is_symlink": path.is_symlink(),
            "owner": path.owner(),
            "group": path.group()
        }

    def set_file_permissions(
        self,
        path: Union[str, Path],
        mode: int,
        recursive: bool = False
    ):
        """Set file permissions with platform-specific handling"""
        path = self.normalize_path(path)

        if recursive and path.is_dir():
            for root, dirs, files in os.walk(path):
                for d in dirs:
                    os.chmod(os.path.join(root, d), mode)
                for f in files:
                    os.chmod(os.path.join(root, f), mode)
        else:
            os.chmod(path, mode)

    def get_disk_usage(self, path: Union[str, Path] = "/") -> Dict[str, int]:
        """Get disk usage information"""
        usage = psutil.disk_usage(str(path))
        return {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": usage.percent
        }

    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        info = {
            "interfaces": {},
            "connections": []
        }

        # Get network interfaces
        for iface, addrs in psutil.net_if_addrs().items():
            info["interfaces"][iface] = []
            for addr in addrs:
                info["interfaces"][iface].append({
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": getattr(addr, "broadcast", None),
                    "ptp": getattr(addr, "ptp", None)
                })

        # Get network connections
        for conn in psutil.net_connections():
            info["connections"].append({
                "fd": conn.fd,
                "family": conn.family,
                "type": conn.type,
                "laddr": conn.laddr._asdict() if conn.laddr else None,
                "raddr": conn.raddr._asdict() if conn.raddr else None,
                "status": conn.status,
                "pid": conn.pid
            })

        return info
