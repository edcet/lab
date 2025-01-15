#!/usr/bin/env zsh

# Integration between Sync Manager and Git Autobuilder
# Provides seamless workflow between environment management and git operations

# Error handling
function __integration_handle_error() {
    local code=$1
    local message=$2
    local context=$3

    __envmgr_log "ERROR" "[${context}] ${message} (code: ${code})"
    return ${code}
}

# Ensure both components are available
function __ensure_components() {
    typeset -f __envmgr_log >/dev/null || {
        echo "Error: Sync Manager not loaded"
        return 1
    }

    typeset -f __auto_commit >/dev/null || {
        echo "Error: Git Autobuilder not loaded"
        return 2
    }

    return 0
}

# Enhanced workspace initialization with environment setup
function init_project() {
    local name="$1"
    local type="${2:-python}"  # Default to Python project
    local path="${3:-./$name}"

    __ensure_components || return $?

    # Initialize git workspace
    __init_workspace "$path" "$type" || {
        __integration_handle_error 3 "Failed to initialize workspace" "project_init"
        return 3
    }

    # Set up environment based on project type
    cd "$path" || {
        __integration_handle_error 4 "Failed to change directory" "project_init"
        return 4
    }

    use_env "$path" || {
        __integration_handle_error 5 "Failed to initialize environment" "project_init"
        return 5
    }

    # Initial commit
    __auto_commit "chore: initial commit" || {
        __integration_handle_error 6 "Failed to create initial commit" "project_init"
        return 6
    }

    __envmgr_log "INFO" "Project initialized successfully at $path"
    return 0
}

# Sync project changes with automatic commits
function sync_project() {
    local path="${1:-.}"
    local message="$2"

    __ensure_components || return $?

    # Ensure we're in a git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        __integration_handle_error 7 "Not a git repository" "project_sync"
        return 7
    }

    # Update environment if needed
    use_env "$path" || {
        __integration_handle_error 8 "Failed to update environment" "project_sync"
        return 8
    }

    # Commit changes if any
    if [[ -n "$(git status --porcelain)" ]]; then
        __auto_commit "${message}" || {
            __integration_handle_error 9 "Failed to commit changes" "project_sync"
            return 9
        }

        __auto_push || {
            __integration_handle_error 10 "Failed to push changes" "project_sync"
            return 10
        }
    else
        __envmgr_log "INFO" "No changes to sync"
    fi

    return 0
}

# Create feature branch with environment isolation
function start_feature() {
    local name="$1"
    local base_branch="${2:-main}"

    __ensure_components || return $?

    # Create feature branch
    local branch="feature/${name}"
    if ! git checkout -b "$branch" "$base_branch"; then
        __integration_handle_error 11 "Failed to create feature branch" "feature_start"
        return 11
    fi

    # Create isolated environment
    local venv_path=".venv-${name}"
    if ! __envmgr_venv_create "$venv_path"; then
        __integration_handle_error 12 "Failed to create isolated environment" "feature_start"
        return 12
    fi

    # Activate isolated environment
    if ! __envmgr_venv_activate "$venv_path"; then
        __integration_handle_error 13 "Failed to activate isolated environment" "feature_start"
        return 13
    fi

    __envmgr_log "INFO" "Feature branch and environment created: $branch"
    return 0
}

# Complete feature with environment cleanup
function complete_feature() {
    local name="$1"
    local target_branch="${2:-main}"

    __ensure_components || return $?

    # Ensure we're on the feature branch
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [[ "$current_branch" != "feature/${name}" ]]; then
        __integration_handle_error 14 "Not on feature branch" "feature_complete"
        return 14
    fi

    # Create PR
    if ! __auto_pr "Complete feature: ${name}"; then
        __integration_handle_error 15 "Failed to create PR" "feature_complete"
        return 15
    fi

    # Clean up isolated environment
    local venv_path=".venv-${name}"
    if [[ -d "$venv_path" ]]; then
        if [[ -n "$VIRTUAL_ENV" && "$VIRTUAL_ENV" == *"$venv_path" ]]; then
            deactivate
        fi
        rm -rf "$venv_path"
    fi

    # Switch back to target branch
    if ! git checkout "$target_branch"; then
        __integration_handle_error 16 "Failed to switch back to target branch" "feature_complete"
        return 16
    fi

    __envmgr_log "INFO" "Feature completed and PR created: $name"
    return 0
}

# Project status overview
function project_status() {
    local path="${1:-.}"

    __ensure_components || return $?

    print -P "%F{blue}Project Status Overview%f"

    # Git status
    print -P "\n%F{yellow}Git Status:%f"
    git status -s

    # Environment status
    print -P "\n%F{yellow}Environment Status:%f"
    envmgr status

    # Recent activity
    print -P "\n%F{yellow}Recent Activity:%f"
    git log --oneline -n 5

    return 0
}

# Register commands
alias pinit='init_project'
alias psync='sync_project'
alias pfeature='start_feature'
alias pcomplete='complete_feature'
alias pstatus='project_status'

# Command completion
function _project_commands() {
    local -a commands
    commands=(
        'pinit:Initialize new project'
        'psync:Sync project changes'
        'pfeature:Start new feature'
        'pcomplete:Complete feature'
        'pstatus:Show project status'
    )
    _describe 'command' commands
}

compdef _project_commands pinit psync pfeature pcomplete pstatus

# Help function
function project_help() {
    print -P "%F{blue}Project Management Commands:%f"
    print -P "  pinit     - Initialize new project"
    print -P "  psync     - Sync project changes"
    print -P "  pfeature  - Start new feature"
    print -P "  pcomplete - Complete feature"
    print -P "  pstatus   - Show project status"
}

# Initialize
__envmgr_log "INFO" "Project management integration loaded"
print -P "%F{green}Project management commands loaded%f"
print -P "%F{blue}Type 'project_help' for available commands%f"
