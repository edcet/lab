#!/bin/bash

# State management tool with self-supporting mechanisms
# This script handles:
# - State inspection
# - Pattern analysis
# - System recovery
# - Health diagnostics

set -e

# Configuration
WORKSPACE_ROOT="/Users/him/lab"
CONFIG_DIR="$WORKSPACE_ROOT/.config"
SYSTEM_CONFIG="$CONFIG_DIR/system/config.json"
STATE_FILE="$CONFIG_DIR/system/state.core"
BACKUP_DIR="$CONFIG_DIR/backups"
CONSCIOUSNESS_CONFIG="$CONFIG_DIR/consciousness/config.json"

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

# State management functions
backup_state() {
    log_info "Backing up system state..."
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/state_$timestamp.bak"

    mkdir -p "$BACKUP_DIR"

    # Backup core state
    cp "$STATE_FILE" "$backup_file"

    # Backup consciousness state
    python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
from consciousness.pattern_network import PatternNetwork
import json

network = PatternNetwork()
state = network.get_network_state()
with open('$backup_file.consciousness', 'w') as f:
    json.dump({
        'coherence': state.coherence,
        'synthesis_depth': state.synthesis_depth,
        'evolution_path': state.evolution_path,
        'emergence_factors': state.emergence_factors
    }, f, indent=2)
"

    log_info "State backed up to $backup_file"
}

restore_state() {
    local backup_file=$1
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file $backup_file not found"
        return 1
    fi

    # Validate state transition
    if ! validate_state_transition "$backup_file"; then
        log_error "Invalid state transition"
        return 1
    }

    # Restore core state
    cp "$backup_file" "$STATE_FILE"

    # Restore consciousness state if available
    if [ -f "$backup_file.consciousness" ]; then
        python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
from consciousness.pattern_network import PatternNetwork
import json

network = PatternNetwork()
with open('$backup_file.consciousness') as f:
    state = json.load(f)
network.restore_state(state)
"
    fi

    log_info "State restored from $backup_file"
}

validate_state_transition() {
    local backup_file=$1
    log_info "Validating state transition..."

    python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
import json
from src.store import RadicalStore
from consciousness.pattern_network import PatternNetwork

def validate_transition(current_file, backup_file):
    # Load states
    with open(current_file) as f:
        current = json.load(f)
    with open(backup_file) as f:
        backup = json.load(f)

    # Validate core state
    store = RadicalStore()
    if not store.validate_state_transition(current, backup):
        sys.exit(1)

    # Validate consciousness state
    if not PatternNetwork().validate_state_transition(current, backup):
        sys.exit(1)

    return True

validate_transition('$STATE_FILE', '$backup_file')
" || {
        log_error "State transition validation failed"
        return 1
    }

    return 0
}

list_backups() {
    log_info "Available state backups:"
    ls -lh "$BACKUP_DIR" | grep "state_" || true
}

# Analysis functions
analyze_patterns() {
    log_info "Analyzing system patterns..."
    python3 - << EOF
import sys
sys.path.append('$WORKSPACE_ROOT')
from src.pattern_system import PatternSystem
from src.store import RadicalStore
from consciousness.pattern_network import PatternNetwork
import json

async def analyze():
    store = RadicalStore()
    system = PatternSystem()
    network = PatternNetwork()

    # Get patterns
    patterns = await store.get_recent_patterns(limit=100)

    # Analyze patterns
    analysis = await system.analyze_patterns(patterns)

    # Get network state
    network_state = network.get_network_state()

    # Calculate evolution metrics
    evolution = {
        'coherence_trend': calculate_coherence_trend(network_state),
        'synthesis_depth': network_state.synthesis_depth,
        'emergence_factors': network_state.emergence_factors
    }

    print("\nPattern Analysis Results:")
    print("-" * 50)
    for category, results in analysis.items():
        print(f"\n{category}:")
        for key, value in results.items():
            print(f"  {key}: {value}")

    print("\nEvolution Analysis:")
    print("-" * 50)
    for key, value in evolution.items():
        print(f"{key}: {value}")

def calculate_coherence_trend(state):
    if not state.evolution_path:
        return 0.0
    return state.coherence - sum(state.evolution_path) / len(state.evolution_path)

import asyncio
asyncio.run(analyze())
EOF
}

check_health() {
    log_info "Checking system health..."

    # Check core services
    local services=(
        "11434:Ollama"
        "1234:LM Studio"
        "4891:TGPT"
    )

    for service in "${services[@]}"; do
        local port=${service%%:*}
        local name=${service#*:}
        nc -z localhost $port &>/dev/null
        if [ $? -eq 0 ]; then
            log_info "$name is running on port $port"
        else
            log_warn "$name is not running on port $port"
        fi
    done

    # Check system state
    if [ -f "$STATE_FILE" ]; then
        log_info "System state file exists"
        python3 - << EOF
import sys
sys.path.append('$WORKSPACE_ROOT')
import json
from src.store import RadicalStore
from consciousness.pattern_network import PatternNetwork

def check_health():
    # Check store health
    store = RadicalStore()
    store_health = store.check_health()

    # Check network health
    network = PatternNetwork()
    network_health = network.check_health()

    # Load state
    with open('$STATE_FILE') as f:
        state = json.load(f)

    print("\nStore Health:")
    print("-" * 50)
    for key, value in store_health.items():
        print(f"{key}: {value}")

    print("\nNetwork Health:")
    print("-" * 50)
    for key, value in network_health.items():
        print(f"{key}: {value}")

    print("\nCurrent System State:")
    print("-" * 50)
    for key, value in state.items():
        print(f"{key}: {value}")

check_health()
EOF
    else
        log_warn "System state file not found"
    fi
}

show_help() {
    cat << EOF
State Management Tool

Usage: $0 [command]

Commands:
  backup              Create state backup
  restore [file]      Restore state from backup
  list               List available backups
  analyze            Analyze system patterns
  health             Check system health
  help               Show this help message

Examples:
  $0 backup
  $0 restore backups/state_20240113_120000.bak
  $0 analyze
EOF
}

# Main function
main() {
    local cmd=${1:-help}
    shift || true

    case $cmd in
        backup)
            backup_state
            ;;
        restore)
            if [ -z "$1" ]; then
                log_error "Backup file required"
                exit 1
            fi
            restore_state "$1"
            ;;
        list)
            list_backups
            ;;
        analyze)
            analyze_patterns
            ;;
        health)
            check_health
            ;;
        help)
            show_help
            ;;
        *)
            log_error "Unknown command: $cmd"
            show_help
            exit 1
            ;;
    esac
}

# Run tool
main "$@"
