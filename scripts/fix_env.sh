#!/bin/bash

# Environment fix script with self-supporting mechanisms
# This script handles:
# - Environment validation
# - Dependency fixes
# - Path corrections
# - Permission repairs

set -e

# Configuration
WORKSPACE_ROOT="/Users/him/lab"
CONFIG_DIR="$WORKSPACE_ROOT/.config"
SYSTEM_CONFIG="$CONFIG_DIR/system/config.json"
AI_CONFIG="$CONFIG_DIR/ai/config.json"
CONSCIOUSNESS_CONFIG="$CONFIG_DIR/consciousness/config.json"
ENV_FILE="$WORKSPACE_ROOT/.env"
VENV_DIR="$WORKSPACE_ROOT/.venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Environment validation functions
check_python_environment() {
    log_info "Checking Python environment..."

    # Check Python version
    local required_version="3.8"
    local current_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')

    if [ "$(printf '%s\n' "$required_version" "$current_version" | sort -V | head -n1)" != "$required_version" ]; then
        log_error "Python version $required_version or higher required (current: $current_version)"
        return 1
    fi

    # Check virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        log_warn "Virtual environment not found, creating..."
        python3 -m venv "$VENV_DIR"
    fi

    # Check dependencies
    if [ -f "$WORKSPACE_ROOT/requirements.txt" ]; then
        log_info "Verifying dependencies..."
        source "$VENV_DIR/bin/activate"
        pip install -r "$WORKSPACE_ROOT/requirements.txt"
    else
        log_error "requirements.txt not found"
        return 1
    fi

    # Check consciousness system dependencies
    python3 -c "
import numpy
import cryptography
import sqlite3
" || {
        log_error "Consciousness system dependencies missing"
        return 1
    }
}

check_environment_variables() {
    log_info "Checking environment variables..."

    # Create .env if not exists
    if [ ! -f "$ENV_FILE" ]; then
        log_warn ".env file not found, creating default..."
        cat > "$ENV_FILE" << EOF
WORKSPACE_ROOT=$WORKSPACE_ROOT
PYTHONPATH=$WORKSPACE_ROOT
CONFIG_DIR=$CONFIG_DIR
SYSTEM_CONFIG=$SYSTEM_CONFIG
AI_CONFIG=$AI_CONFIG
CONSCIOUSNESS_CONFIG=$CONSCIOUSNESS_CONFIG

# LLM Provider Endpoints
OLLAMA_ENDPOINT=http://localhost:11434
LMSTUDIO_ENDPOINT=http://localhost:1234
TGPT_ENDPOINT=http://localhost:4891

# Pattern Network Configuration
PATTERN_DB=$CONSCIOUSNESS_CONFIG/patterns.db
PATTERN_NETWORK_LOG=$WORKSPACE_ROOT/logs/pattern_network.log
EOF
    fi

    # Source environment variables
    set -a
    source "$ENV_FILE"
    set +a

    # Verify required variables
    local required_vars=(
        "WORKSPACE_ROOT"
        "PYTHONPATH"
        "CONFIG_DIR"
        "SYSTEM_CONFIG"
        "AI_CONFIG"
        "CONSCIOUSNESS_CONFIG"
        "OLLAMA_ENDPOINT"
        "LMSTUDIO_ENDPOINT"
        "TGPT_ENDPOINT"
        "PATTERN_DB"
        "PATTERN_NETWORK_LOG"
    )
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required environment variable $var not set"
            return 1
        fi
    done
}

fix_permissions() {
    log_info "Fixing permissions..."

    # Fix directory permissions
    local dirs=(
        "$WORKSPACE_ROOT/src"
        "$CONFIG_DIR"
        "$WORKSPACE_ROOT/data"
        "$WORKSPACE_ROOT/logs"
        "$WORKSPACE_ROOT/models"
        "$CONSCIOUSNESS_CONFIG"
    )

    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            chmod 755 "$dir"
            log_debug "Fixed permissions for $dir"
        fi
    done

    # Fix file permissions
    find "$WORKSPACE_ROOT/scripts" -type f -name "*.sh" -exec chmod 755 {} \;
    find "$WORKSPACE_ROOT/src" -type f -name "*.py" -exec chmod 644 {} \;
    find "$CONFIG_DIR" -type f -name "*.json" -exec chmod 644 {} \;

    # Fix consciousness system files
    if [ -f "$PATTERN_DB" ]; then
        chmod 644 "$PATTERN_DB"
        log_debug "Fixed permissions for pattern database"
    fi
}

fix_paths() {
    log_info "Fixing paths..."

    # Add workspace to PYTHONPATH
    if [[ ":$PYTHONPATH:" != *":$WORKSPACE_ROOT:"* ]]; then
        echo "export PYTHONPATH=$WORKSPACE_ROOT:\$PYTHONPATH" >> "$ENV_FILE"
        log_info "Added workspace to PYTHONPATH"
    fi

    # Fix shell configuration
    local shell_config="$HOME/.zshrc"
    if [ -f "$shell_config" ]; then
        if ! grep -q "source.*$ENV_FILE" "$shell_config"; then
            echo "source $ENV_FILE" >> "$shell_config"
            log_info "Added environment sourcing to shell config"
        fi
    fi
}

check_llm_providers() {
    log_info "Checking LLM provider configurations..."

    # Check Ollama
    if ! command -v ollama &> /dev/null; then
        log_warn "Ollama not found, please install from https://ollama.ai"
        return 1
    fi

    # Check LM Studio
    if ! pgrep -f "LM Studio" &> /dev/null; then
        log_warn "LM Studio not running, please install from https://lmstudio.ai"
    fi

    # Check TGPT
    if ! command -v tgpt &> /dev/null; then
        log_warn "TGPT not found, please install from https://github.com/aandrew-me/tgpt"
        return 1
    fi

    # Verify provider configurations
    python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
import json
import aiohttp
import asyncio

async def check_providers():
    # Load AI config
    with open('$AI_CONFIG') as f:
        config = json.load(f)

    async with aiohttp.ClientSession() as session:
        # Check Ollama
        try:
            async with session.get(config['providers']['ollama']['endpoint']) as resp:
                if resp.status != 200:
                    print('Ollama endpoint not responding')
                    sys.exit(1)
        except:
            print('Failed to connect to Ollama')
            sys.exit(1)

        # Check LM Studio
        try:
            async with session.get(config['providers']['lmstudio']['endpoint']) as resp:
                if resp.status != 200:
                    print('LM Studio endpoint not responding')
        except:
            print('Failed to connect to LM Studio')

        # Check TGPT
        try:
            async with session.get(config['providers']['tgpt']['endpoint']) as resp:
                if resp.status != 200:
                    print('TGPT endpoint not responding')
                    sys.exit(1)
        except:
            print('Failed to connect to TGPT')
            sys.exit(1)

asyncio.run(check_providers())
" || {
        log_error "LLM provider configuration check failed"
        return 1
    }
}

setup_consciousness_system() {
    log_info "Setting up consciousness system..."

    # Create pattern database
    if [ ! -f "$PATTERN_DB" ]; then
        log_warn "Pattern database not found, initializing..."
        python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
import sqlite3
import json

# Create database
conn = sqlite3.connect('$PATTERN_DB')
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS patterns (
    id TEXT PRIMARY KEY,
    type TEXT,
    components TEXT,
    relationships TEXT,
    metadata TEXT,
    timestamp REAL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS connections (
    source_id TEXT,
    target_id TEXT,
    strength REAL,
    type TEXT,
    metadata TEXT,
    FOREIGN KEY(source_id) REFERENCES patterns(id),
    FOREIGN KEY(target_id) REFERENCES patterns(id)
)
''')

conn.commit()
conn.close()
"
    fi

    # Create log directory
    mkdir -p "$(dirname "$PATTERN_NETWORK_LOG")"
    touch "$PATTERN_NETWORK_LOG"
}

verify_fixes() {
    log_info "Verifying fixes..."

    # Verify Python imports
    python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
try:
    from src.system import UnifiedSystem
    from src.store import RadicalStore
    from src.pattern_system import PatternSystem
    from consciousness.pattern_network import PatternNetwork
    print('Python imports verified successfully')
except ImportError as e:
    print(f'Import verification failed: {e}')
    sys.exit(1)
"

    # Verify permissions
    if [ ! -x "$WORKSPACE_ROOT/scripts/start.sh" ]; then
        log_error "Permission verification failed"
        return 1
    fi

    # Verify environment
    if [ -z "$PYTHONPATH" ] || [[ ":$PYTHONPATH:" != *":$WORKSPACE_ROOT:"* ]]; then
        log_error "Path verification failed"
        return 1
    fi

    # Verify consciousness system
    python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
from consciousness.pattern_network import PatternNetwork
import sqlite3

# Check database
conn = sqlite3.connect('$PATTERN_DB')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\'')
tables = cursor.fetchall()
if not any('patterns' in t for t in tables):
    sys.exit(1)
conn.close()

# Check network initialization
network = PatternNetwork()
if not network.is_initialized():
    sys.exit(1)
" || {
        log_error "Consciousness system verification failed"
        return 1
    }
}

# Main function
main() {
    log_info "Starting environment fixes..."

    # Check and fix Python environment
    check_python_environment || exit 1

    # Check and fix environment variables
    check_environment_variables || exit 1

    # Check LLM providers
    check_llm_providers || exit 1

    # Setup consciousness system
    setup_consciousness_system || exit 1

    # Fix permissions
    fix_permissions || exit 1

    # Fix paths
    fix_paths || exit 1

    # Verify all fixes
    verify_fixes || exit 1

    log_info "Environment fixes completed successfully"
}

# Run fixes
main
