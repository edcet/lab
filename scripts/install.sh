#!/bin/bash

# System installation script with self-supporting mechanisms
# This script handles:
# - System dependencies
# - Configuration setup
# - Integration verification
# - Self-healing capabilities

set -e

# Configuration
WORKSPACE_ROOT="/Users/him/lab"
CONFIG_DIR="$WORKSPACE_ROOT/.config"
SYSTEM_CONFIG="$CONFIG_DIR/system"
AI_CONFIG="$CONFIG_DIR/ai"
CONSCIOUSNESS_CONFIG="$CONFIG_DIR/consciousness"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Self-healing functions
verify_directory() {
    local dir=$1
    if [ ! -d "$dir" ]; then
        log_warn "Directory $dir missing, creating..."
        mkdir -p "$dir"
    fi
}

verify_file() {
    local file=$1
    local template=$2
    if [ ! -f "$file" ]; then
        log_warn "File $file missing, creating from template..."
        cp "$template" "$file"
    fi
}

verify_dependencies() {
    local deps=("python3" "pip3" "git" "zsh")
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            log_error "$dep is required but not installed"
            exit 1
        fi
    done
}

# LLM provider validation
verify_llm_providers() {
    log_info "Verifying LLM providers..."

    # Check Ollama
    if ! command -v ollama &> /dev/null; then
        log_warn "Ollama not found, installing..."
        curl https://ollama.ai/install.sh | sh
    fi

    # Check LM Studio
    if ! pgrep -f "LM Studio" &> /dev/null; then
        log_warn "Please install LM Studio from https://lmstudio.ai"
    fi

    # Check TGPT
    if ! command -v tgpt &> /dev/null; then
        log_warn "Please install TGPT from https://github.com/aandrew-me/tgpt"
    fi
}

# Setup functions
setup_directories() {
    log_info "Setting up directory structure..."
    local dirs=(
        "$CONFIG_DIR"
        "$SYSTEM_CONFIG"
        "$AI_CONFIG"
        "$CONSCIOUSNESS_CONFIG"
        "$WORKSPACE_ROOT/data"
        "$WORKSPACE_ROOT/logs"
        "$WORKSPACE_ROOT/models"
        "$WORKSPACE_ROOT/backups"
    )

    for dir in "${dirs[@]}"; do
        verify_directory "$dir"
    done
}

setup_python_environment() {
    log_info "Setting up Python environment..."

    # Create requirements.txt if missing
    if [ ! -f "$WORKSPACE_ROOT/requirements.txt" ]; then
        log_warn "Creating requirements.txt..."
        cat > "$WORKSPACE_ROOT/requirements.txt" << EOF
numpy>=1.21.0
cryptography>=3.4.7
aiohttp>=3.8.1
sqlalchemy>=1.4.0
pyyaml>=5.4.1
python-dotenv>=0.19.0
EOF
    fi

    # Create setup.py if missing
    if [ ! -f "$WORKSPACE_ROOT/setup.py" ]; then
        log_warn "Creating setup.py..."
        cat > "$WORKSPACE_ROOT/setup.py" << EOF
from setuptools import setup, find_packages

setup(
    name="radical-system",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0",
        "cryptography>=3.4.7",
        "aiohttp>=3.8.1",
        "sqlalchemy>=1.4.0",
        "pyyaml>=5.4.1",
        "python-dotenv>=0.19.0",
    ],
    python_requires=">=3.8",
)
EOF
    fi

    python3 -m pip install -r "$WORKSPACE_ROOT/requirements.txt"
    python3 -m pip install -e "$WORKSPACE_ROOT"
}

setup_configurations() {
    log_info "Setting up configurations..."

    # System config
    if [ ! -f "$SYSTEM_CONFIG/config.json" ]; then
        log_warn "System config missing, creating default..."
        cat > "$SYSTEM_CONFIG/config.json" << EOF
{
    "workspace_root": "$WORKSPACE_ROOT",
    "config_dir": "$CONFIG_DIR",
    "data_dir": "$WORKSPACE_ROOT/data",
    "logs_dir": "$WORKSPACE_ROOT/logs",
    "models_dir": "$WORKSPACE_ROOT/models",
    "backups_dir": "$WORKSPACE_ROOT/backups",
    "state_file": "$SYSTEM_CONFIG/state.core",
    "debug": true,
    "log_level": "INFO"
}
EOF
    fi

    # AI config
    if [ ! -f "$AI_CONFIG/config.json" ]; then
        log_warn "AI config missing, creating default..."
        cat > "$AI_CONFIG/config.json" << EOF
{
    "providers": {
        "ollama": {
            "endpoint": "http://localhost:11434",
            "models": ["codellama", "llama2"],
            "default_model": "codellama"
        },
        "lmstudio": {
            "endpoint": "http://localhost:1234",
            "models": ["local"],
            "default_model": "local"
        },
        "tgpt": {
            "endpoint": "http://localhost:4891",
            "models": ["gpt-3.5-turbo"],
            "default_model": "gpt-3.5-turbo"
        }
    },
    "default_provider": "ollama",
    "cache_dir": "$AI_CONFIG/cache",
    "max_tokens": 2048,
    "temperature": 0.7
}
EOF
    fi

    # Consciousness config
    if [ ! -f "$CONSCIOUSNESS_CONFIG/config.json" ]; then
        log_warn "Consciousness config missing, creating default..."
        cat > "$CONSCIOUSNESS_CONFIG/config.json" << EOF
{
    "pattern_network": {
        "storage": {
            "type": "sqlite",
            "path": "$CONSCIOUSNESS_CONFIG/patterns.db"
        },
        "evolution": {
            "learning_rate": 0.1,
            "coherence_threshold": 0.7,
            "emergence_threshold": 0.8
        },
        "metrics": {
            "track_evolution": true,
            "track_emergence": true,
            "history_size": 1000
        }
    },
    "integration": {
        "sync_interval": 60,
        "batch_size": 100,
        "max_patterns": 10000
    }
}
EOF
    fi
}

verify_installation() {
    log_info "Verifying installation..."

    # Check core files
    local core_files=(
        "src/main.py"
        "src/system.py"
        "src/store.py"
        "src/pattern_system.py"
        ".config/consciousness/pattern_network.py"
    )

    for file in "${core_files[@]}"; do
        if [ ! -f "$WORKSPACE_ROOT/$file" ]; then
            log_error "Core file $file missing"
            exit 1
        fi
    done

    # Verify Python imports
    python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
from src.system import UnifiedSystem
from src.store import RadicalStore
from src.pattern_system import PatternSystem
from consciousness.pattern_network import PatternNetwork
" || {
        log_error "Python imports verification failed"
        exit 1
    }

    # Verify configurations
    local config_files=(
        "$SYSTEM_CONFIG/config.json"
        "$AI_CONFIG/config.json"
        "$CONSCIOUSNESS_CONFIG/config.json"
    )

    for config in "${config_files[@]}"; do
        if [ ! -f "$config" ]; then
            log_error "Config file $config missing"
            exit 1
        fi

        # Validate JSON
        if ! python3 -c "import json; json.load(open('$config'))"; then
            log_error "Invalid JSON in $config"
            exit 1
        fi
    done
}

# Main installation
main() {
    log_info "Starting installation..."

    # Verify system dependencies
    verify_dependencies

    # Verify LLM providers
    verify_llm_providers

    # Setup directory structure
    setup_directories

    # Setup Python environment
    setup_python_environment

    # Setup configurations
    setup_configurations

    # Verify installation
    verify_installation

    log_info "Installation completed successfully"
}

# Run installation
main
