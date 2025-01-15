#!/bin/zsh

# Advanced PATH Management System
# Handles paths with priority levels and environment awareness

# Initialize path arrays by priority
typeset -U path
typeset -ga high_priority_paths=()
typeset -ga project_paths=()
typeset -ga tool_paths=()
typeset -ga system_paths=()
typeset -ga user_paths=()

# Function to add paths with priority
function path_add() {
    local priority="$1"
    shift
    local new_paths=("$@")

    case "$priority" in
        high)    high_priority_paths+=($new_paths) ;;
        project) project_paths+=($new_paths) ;;
        tool)    tool_paths+=($new_paths) ;;
        system)  system_paths+=($new_paths) ;;
        user)    user_paths+=($new_paths) ;;
    esac
}

# High Priority Paths (Virtual Environments)
if [[ -n "$VIRTUAL_ENV" ]]; then
    path_add high "$VIRTUAL_ENV/bin"
fi

# Project-specific paths
if [[ -d "node_modules/.bin" ]]; then
    path_add project "node_modules/.bin"
fi

# Tool paths (Homebrew, etc.)
if [[ "$(uname -m)" == "arm64" ]]; then
    path_add tool "/opt/homebrew/bin" "/opt/homebrew/sbin"
fi

# System paths
path_add system \
    /usr/local/bin \
    /usr/bin \
    /bin \
    /usr/local/sbin \
    /usr/sbin \
    /sbin

# User paths
path_add user \
    "$HOME/.local/bin" \
    "$HOME/bin" \
    "$HOME/.cargo/bin"

# Construct final PATH maintaining priority
path=(
    $high_priority_paths
    $project_paths
    $tool_paths
    $system_paths
    $user_paths
)

# Ensure uniqueness and export
typeset -U PATH
export PATH

# Function to display path by priority
function paths() {
    echo "\033[1;34mHigh Priority Paths:\033[0m"
    print -l $high_priority_paths
    echo "\033[1;32mProject Paths:\033[0m"
    print -l $project_paths
    echo "\033[1;33mTool Paths:\033[0m"
    print -l $tool_paths
    echo "\033[1;36mSystem Paths:\033[0m"
    print -l $system_paths
    echo "\033[1;35mUser Paths:\033[0m"
    print -l $user_paths
}
