"""NFX Utilities Module

Advanced utility functions for NFX with integrated AutoGPT functionality.
Includes system checks, environment management, and helper functions.
"""
import asyncio
import contextlib
import functools
import logging
import os
import re
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional, ParamSpec, TypeVar, Union, cast

import aiohttp
import requests
from colorama import Fore, Style
from git import InvalidGitRepositoryError, Repo

P = ParamSpec("P")
T = TypeVar("T")

logger = logging.getLogger(__name__)

# System Paths
NFX_ROOT = Path(__file__).parent.parent.parent
ENV_FILE_PATH = NFX_ROOT / ".env"
DATA_DIR = NFX_ROOT / "data"
LOGS_DIR = NFX_ROOT / "logs"

# Neural Constants
NEURAL_PATTERNS = {
    "ALPHA": [1, 0, 1, 1, 0],
    "BETA": [0, 1, 1, 0, 1],
    "GAMMA": [1, 1, 0, 1, 0],
    "DELTA": [0, 0, 1, 1, 1],
    "OMEGA": [1, 1, 1, 0, 0]
}

# Environment Management
def env_file_exists() -> bool:
    """Check if .env file exists"""
    return ENV_FILE_PATH.is_file()

def set_env_config_value(key: str, value: str) -> None:
    """Sets the specified env variable and updates it in .env"""
    os.environ[key] = value

    with ENV_FILE_PATH.open("r+") as file:
        lines = file.readlines()
        file.seek(0)
        key_already_in_file = False
        for line in lines:
            if re.match(rf"^(?:# )?{key}=.*$", line):
                file.write(f"{key}={value}\n")
                key_already_in_file = True
            else:
                file.write(line)

        if not key_already_in_file:
            file.write(f"{key}={value}\n")

        file.truncate()

# System Checks
def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False

def check_python_version() -> bool:
    """Check if Python version meets requirements"""
    if sys.version_info < (3, 10):
        logger.error(
            "WARNING: You are running on an older version of Python. "
            "Please upgrade to Python 3.10 or higher."
        )
        return False
    return True

# Neural Utilities
def generate_neural_signature() -> str:
    """Generate a unique neural signature"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"nfx_{timestamp}"

def validate_neural_pattern(pattern: List[int]) -> bool:
    """Validate a neural pattern"""
    if not pattern or len(pattern) != 5:
        return False
    return all(x in (0, 1) for x in pattern)

def match_neural_pattern(pattern: List[int]) -> Optional[str]:
    """Match a neural pattern to known patterns"""
    for name, known_pattern in NEURAL_PATTERNS.items():
        if pattern == known_pattern:
            return name
    return None

# Async Utilities
def coroutine(f: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, T]:
    """Decorator to run coroutines"""
    @functools.wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

async def fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch content from URL with timeout"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    return await response.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(f"Error fetching URL {url}: {e}")
    return None

# File System Utilities
def ensure_directory(path: Path) -> None:
    """Ensure a directory exists"""
    path.mkdir(parents=True, exist_ok=True)

def clean_directory(path: Path, pattern: str = "*") -> None:
    """Clean files in directory matching pattern"""
    for item in path.glob(pattern):
        if item.is_file():
            item.unlink()

def get_file_checksum(path: Path) -> str:
    """Get file checksum"""
    import hashlib

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

# Git Utilities
def get_current_git_branch() -> str:
    """Get current git branch name"""
    try:
        repo = Repo(search_parent_directories=True)
        branch = repo.active_branch
        return branch.name
    except InvalidGitRepositoryError:
        return ""

def get_git_user_email() -> str:
    """Get git user email"""
    try:
        repo = Repo(search_parent_directories=True)
        return cast(str, repo.config_reader().get_value("user", "email", default=""))
    except InvalidGitRepositoryError:
        return ""

def vcs_state_diverges_from_master() -> bool:
    """Check if git state diverges from master"""
    try:
        repo = Repo(search_parent_directories=True)

        # Check for uncommitted changes
        if repo.index.diff(None):
            return True

        # Check for unpushed commits
        master = repo.heads.master
        current = repo.active_branch

        if current != master:
            return True

        if list(repo.iter_commits("master..HEAD")):
            return True

        return False
    except InvalidGitRepositoryError:
        return False

# Formatting Utilities
def markdown_to_ansi_style(markdown: str) -> str:
    """Convert markdown to ANSI styled text"""
    ansi_lines: list[str] = []
    for line in markdown.split("\n"):
        line_style = ""

        if line.startswith("# "):
            line_style += Style.BRIGHT
        else:
            line = re.sub(
                r"(?<!\*)\*(\*?[^*]+\*?)\*(?!\*)",
                rf"{Style.BRIGHT}\1{Style.NORMAL}",
                line,
            )

        if re.match(r"^#+ ", line) is not None:
            line_style += Fore.CYAN
            line = re.sub(r"^#+ ", "", line)

        ansi_lines.append(f"{line_style}{line}{Style.RESET_ALL}")
    return "\n".join(ansi_lines)

# Neural Memory Utilities
def allocate_memory_pool(size: int) -> memoryview:
    """Allocate a memory pool of specified size"""
    import mmap
    return memoryview(mmap.mmap(-1, size))

def free_memory_pool(pool: memoryview) -> None:
    """Free a memory pool"""
    pool.release()

def memory_pattern_match(data: bytes, pattern: bytes) -> List[int]:
    """Find pattern matches in memory data"""
    matches = []
    pos = 0
    while True:
        pos = data.find(pattern, pos)
        if pos == -1:
            break
        matches.append(pos)
        pos += 1
    return matches
