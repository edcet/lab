#!/bin/bash

# System startup script with self-supporting mechanisms
# This script handles:
# - System initialization
# - Component startup
# - Health checking
# - Auto-recovery

set -e

# Configuration
WORKSPACE_ROOT="/Users/him/lab"
CONFIG_DIR="$WORKSPACE_ROOT/.config"
SYSTEM_CONFIG="$CONFIG_DIR/system/config.json"
AI_CONFIG="$CONFIG_DIR/ai/config.json"
CONSCIOUSNESS_CONFIG="$CONFIG_DIR/consciousness/config.json"
LOG_DIR="$WORKSPACE_ROOT/logs"
PID_FILE="/tmp/radical_system.pid"
STARTUP_LOCK="/tmp/radical_system.lock"

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

# Health check functions
check_port() {
    local port=$1
    nc -z localhost $port &>/dev/null
    return $?
}

wait_for_port() {
    local port=$1
    local service=$2
    local retries=30
    local count=0

    while ! check_port $port; do
        count=$((count + 1))
        if [ $count -eq $retries ]; then
            log_error "$service failed to start on port $port"
            return 1
        fi
        log_warn "Waiting for $service to start on port $port..."
        sleep 1
    done

    log_info "$service started successfully on port $port"
    return 0
}

# Component startup functions
start_llm_providers() {
    log_info "Starting LLM providers..."

    # Start Ollama (11434)
    if ! check_port 11434; then
        ollama serve &>/dev/null &
        wait_for_port 11434 "Ollama" || {
            log_error "Failed to start Ollama"
            return 1
        }
    fi

    # Start LM Studio (1234)
    if ! check_port 1234; then
        log_warn "Please start LM Studio manually on port 1234"
        # Wait for user to start LM Studio
        wait_for_port 1234 "LM Studio" || {
            log_error "LM Studio not started"
            return 1
        }
    fi

    # Start TGPT (4891)
    if ! check_port 4891; then
        log_warn "Please start TGPT manually on port 4891"
        # Wait for user to start TGPT
        wait_for_port 4891 "TGPT" || {
            log_error "TGPT not started"
            return 1
        }
    fi

    return 0
}

start_consciousness_system() {
    log_info "Starting consciousness system..."

    # Start the pattern network
    python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
import asyncio
from consciousness.pattern_network import PatternNetwork

async def start():
    network = PatternNetwork()
    if not await network.initialize():
        sys.exit(1)

asyncio.run(start())
" || {
        log_error "Failed to start consciousness system"
        return 1
    }

    log_info "Consciousness system started successfully"
    return 0
}

start_core_system() {
    log_info "Starting core system..."

    # Start the unified system
    python3 "$WORKSPACE_ROOT/src/main.py" &
    local pid=$!
    echo $pid > $PID_FILE

    # Wait for system initialization
    sleep 2
    if ! kill -0 $pid 2>/dev/null; then
        log_error "Core system failed to start"
        return 1
    fi

    # Verify system state
    if ! python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
from src.store import RadicalStore
store = RadicalStore()
if not store.is_initialized():
    sys.exit(1)
"; then
        log_error "Core system state verification failed"
        kill $pid 2>/dev/null
        return 1
    fi

    log_info "Core system started successfully (PID: $pid)"
    return 0
}

start_monitoring() {
    log_info "Starting monitoring system..."

    # Start the monitoring system
    python3 "$WORKSPACE_ROOT/src/monitoring/monitor.py" &>/dev/null &
    local pid=$!

    # Verify monitoring system
    sleep 1
    if ! kill -0 $pid 2>/dev/null; then
        log_error "Monitoring system failed to start"
        return 1
    fi

    # Verify metrics collection
    if ! python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
from src.monitoring.metrics import MetricsCollector
collector = MetricsCollector()
if not collector.is_collecting():
    sys.exit(1)
"; then
        log_error "Metrics collection verification failed"
        kill $pid 2>/dev/null
        return 1
    fi

    log_info "Monitoring system started successfully"
    return 0
}

# Recovery functions
recover_failed_component() {
    local component=$1
    log_warn "Attempting to recover $component..."

    case $component in
        "consciousness")
            start_consciousness_system
            ;;
        "core")
            start_core_system
            ;;
        "monitoring")
            start_monitoring
            ;;
        *)
            log_error "Unknown component: $component"
            return 1
            ;;
    esac

    return $?
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    if [ -f $PID_FILE ]; then
        kill $(cat $PID_FILE) 2>/dev/null || true
        rm $PID_FILE
    fi
    if [ -f $STARTUP_LOCK ]; then
        rm $STARTUP_LOCK
    fi
}

# Main startup
main() {
    # Check if already running
    if [ -f $STARTUP_LOCK ]; then
        log_error "Another instance is starting up"
        exit 1
    fi

    # Create startup lock
    touch $STARTUP_LOCK

    # Register cleanup
    trap cleanup EXIT

    log_info "Starting system..."

    # Start components in order
    components=(
        "llm_providers"
        "consciousness"
        "core"
        "monitoring"
    )

    for component in "${components[@]}"; do
        case $component in
            "llm_providers")
                start_llm_providers || exit 1
                ;;
            "consciousness")
                start_consciousness_system || exit 1
                ;;
            "core")
                start_core_system || exit 1
                ;;
            "monitoring")
                start_monitoring || exit 1
                ;;
        esac
    done

    log_info "System started successfully"

    # Keep script running and monitor system health
    while true; do
        if [ -f $PID_FILE ]; then
            if ! kill -0 $(cat $PID_FILE) 2>/dev/null; then
                log_error "Core system crashed, attempting recovery..."
                if ! recover_failed_component "core"; then
                    log_error "Core system recovery failed"
                    exit 1
                fi
            fi
        fi

        # Check consciousness system
        if ! python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
from consciousness.pattern_network import PatternNetwork
network = PatternNetwork()
if not network.is_healthy():
    sys.exit(1)
" 2>/dev/null; then
            log_error "Consciousness system unhealthy, attempting recovery..."
            if ! recover_failed_component "consciousness"; then
                log_error "Consciousness system recovery failed"
                exit 1
            fi
        fi

        # Check monitoring system
        if ! python3 -c "
import sys
sys.path.append('$WORKSPACE_ROOT')
from src.monitoring.metrics import MetricsCollector
collector = MetricsCollector()
if not collector.is_collecting():
    sys.exit(1)
" 2>/dev/null; then
            log_error "Monitoring system unhealthy, attempting recovery..."
            if ! recover_failed_component "monitoring"; then
                log_error "Monitoring system recovery failed"
                exit 1
            fi
        fi

        sleep 5
    done
}

# Run startup
main
