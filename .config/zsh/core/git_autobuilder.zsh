#!/usr/bin/env zsh

# Git Autobuilder: Automated Git Operations

# State tracking
typeset -g GIT_AUTOBUILDER_LOADED=0
[[ "$GIT_AUTOBUILDER_LOADED" == "1" ]] && return 0

# Requirements
command -v git >/dev/null 2>&1 || {
    print -P "%F{red}Error: git command not found%f"
    return 1
}

# Core functions
function git_commit() {
    local msg="$1"
    git add -A && git commit -m "$msg"
}

function git_push() {
    local branch="$(git rev-parse --abbrev-ref HEAD)"
    git push origin "$branch"
}

function git_pr() {
    local title="$1"
    local body="$2"
    gh pr create --title "$title" ${body:+--body "$body"}
}

function git_init() {
    local name="${1:-${PWD:t}}"
    git init && git add . && git commit -m "init: $name"
}

# Register commands
alias gac='git_commit'
alias gap='git_push'
alias gapr='git_pr'
alias gwi='git_init'

GIT_AUTOBUILDER_LOADED=1

function __ensure_command {
    command -v "$1" >/dev/null 2>&1
}

# Initialize state
typeset -gA GIT_AUTOBUILDER_STATE=()

# Enable Zsh-specific options
setopt EXTENDED_GLOB
setopt SH_WORD_SPLIT
setopt KSH_ARRAYS

# Error handling
function __handle_error() {
    local code=$1
    local message=$2
    local context=$3

    __log "ERROR" "[${context}] ${message} (code: ${code})"
    return ${code}
}

function __ensure_git_repo() {
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        __handle_error 1 "Not a git repository" "repository_check"
        return 1
    fi
    return 0
}

function __ensure_clean_workspace() {
    if [[ -n "$(git status --porcelain)" ]]; then
        return 0
    fi
    __handle_error 2 "No changes to commit" "workspace_check"
    return 2
}

function __ensure_command() {
    local cmd=$1
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        __handle_error 3 "Command not found: ${cmd}" "command_check"
        return 3
    fi
    return 0
}

# Ensure XDG directories exist
typeset -g XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
typeset -g XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
typeset -g XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"

# Create necessary directories
mkdir -p "${XDG_CONFIG_HOME}/git-autobuilder"
mkdir -p "${XDG_DATA_HOME}/git-autobuilder/logs"
mkdir -p "${XDG_CACHE_HOME}/git-autobuilder"

# Configuration paths
typeset -g __GIT_AUTOBUILDER_CONFIG="${XDG_CONFIG_HOME}/git-autobuilder/config.toml"
typeset -g __GIT_AUTOBUILDER_LOG="${XDG_DATA_HOME}/git-autobuilder/logs/automation.log"
typeset -g __GIT_AUTOBUILDER_AI_LOG="${XDG_DATA_HOME}/git-autobuilder/logs/ai.log"
typeset -g __GIT_AUTOBUILDER_WEBHOOK_LOG="${XDG_DATA_HOME}/git-autobuilder/logs/webhooks.log"

# Logging functions
function __log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" >> "${__GIT_AUTOBUILDER_LOG}"
}

function __log_ai() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" >> "${__GIT_AUTOBUILDER_AI_LOG}"
}

function __log_webhook() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" >> "${__GIT_AUTOBUILDER_WEBHOOK_LOG}"
}

# AI-powered commit message generation
function __generate_commit_message() {
    local message="$1"
    local files=()
    local tmpfile=$(mktemp)

    if ! git diff --cached --name-only > "$tmpfile"; then
        __handle_error 4 "Failed to get changed files" "commit_message"
        rm -f "$tmpfile"
        return 4
    fi

    while IFS= read -r file; do
        [[ -n "$file" ]] || continue
        files+=("$file")
    done < "$tmpfile"
    rm -f "$tmpfile"

    if [[ ${#files[@]} -eq 0 ]]; then
        __handle_error 5 "No files staged for commit" "commit_message"
        return 5
    fi

    if [[ -z "${message}" ]]; then
        local type="chore"
        local scope="misc"
        
        # Join files with spaces for pattern matching
        local file_list="${files[*]}"
        if [[ "$file_list" =~ \.(md|rst)$ ]]; then
            type="docs"
        elif [[ "$file_list" =~ \.(py|js|ts|go|rs)$ ]]; then
            type="feat"
        elif [[ "$file_list" =~ (test_|_test|\.(spec|test))\. ]]; then
            type="test"
        elif [[ "$file_list" =~ \.(css|scss|less)$ ]]; then
            type="style"
        fi
        
        message="${type}(${scope}): update ${#files} files"
    fi

    echo "${message}"
    return 0
}

# Workspace initialization
function __init_workspace() {
    local path="${1:-.}"
    local template="${2:-}"

    if [[ -d "${path}/.git" ]]; then
        __handle_error 6 "Git repository already exists" "workspace_init"
        return 6
    fi

    if ! mkdir -p "${path}"; then
        __handle_error 7 "Failed to create directory" "workspace_init"
        return 7
    fi

    if ! cd "${path}"; then
        __handle_error 8 "Failed to change directory" "workspace_init"
        return 8
    fi

    if ! git init; then
        __handle_error 9 "Failed to initialize git repository" "workspace_init"
        return 9
    fi
    case "${template}" in
        python)
            cat > pyproject.toml << 'EOL' || __handle_error 10 "Failed to create pyproject.toml" "workspace_init"
[project]
name = "project"
version = "0.1.0"
description = ""

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOL
            ;;
        node)
            if ! __ensure_command "npm"; then
                return 3
            fi
            npm init -y || __handle_error 11 "Failed to initialize npm project" "workspace_init"
            ;;
    esac

    __log "INFO" "Initialized workspace at ${path}"
    return 0
}

# Workspace scanning
function __scan_workspace() {
    local path="${1:-.}"
    local depth="${2:-3}"
    local repos=()
    local tmpfile=$(mktemp)
    local repo
    
    # Find git repositories
    if ! find "${path}" -maxdepth "${depth}" -name .git -type d -exec dirname {} \; > "$tmpfile"; then
        __handle_error 12 "Failed to scan workspace" "workspace_scan"
        rm -f "$tmpfile"
        return 12
    fi
    
    # Read repositories
    while IFS= read -r repo; do
        [[ -n "$repo" ]] || continue
        repos+=("$repo")
    done < "$tmpfile"
    rm -f "$tmpfile"
    
    # Check results
    if [[ ${#repos[@]} -eq 0 ]]; then
        __log "WARN" "No git repositories found in ${path}"
        return 0
    fi
    
    # Process repositories
    local current_repo
    for current_repo in "${repos[@]}"; do
        if ! cd "${current_repo}"; then
            __log "ERROR" "Failed to access repository: ${current_repo}"
            continue
        fi
        
        # Process repository
        __log "INFO" "Processing repository: ${current_repo}"
        local remote=$(git remote get-url origin 2>/dev/null)
        echo "Found repository: ${current_repo} (${remote:-no remote})"
    done
    
    return 0
}

# Workspace monitoring
function __monitor_workspace() {
    local path="${1:-.}"
    local interval="${2:-300}"

    if ! __ensure_command "git"; then
        return 3
    fi

    __log "INFO" "Starting workspace monitor for ${path}"

    while true; do
        local repos=()
        local tmpfile=$(mktemp)
        if ! find "${path}" -name .git -type d -exec dirname {} \; > "$tmpfile"; then
            __handle_error 13 "Failed to scan workspace" "workspace_monitor"
            rm -f "$tmpfile"
            sleep "${interval}"
            continue
        fi

        while IFS= read -r repo; do
            [[ -n "$repo" ]] || continue
            repos+=("$repo")
        done < "$tmpfile"
        rm -f "$tmpfile"

        for repo in "${repos[@]}"; do
            if ! cd "${repo}"; then
                __log "WARN" "Failed to access repository: ${repo}"
                continue
            }

            if git status --porcelain | grep -q '^.M'; then
                __log "INFO" "Changes detected in ${repo}"
                local message
                if ! message=$(__generate_commit_message); then
                    __log "WARN" "Failed to generate commit message for ${repo}"
                    continue
                fi

                if ! git add -A; then
                    __log "WARN" "Failed to stage changes in ${repo}"
                    continue
                }

                if ! git commit -m "${message}"; then
                    __log "WARN" "Failed to commit changes in ${repo}"
                    continue
                }

                if ! git push; then
                    __log "WARN" "Failed to push changes in ${repo}"
                    continue
                }

                __log "INFO" "Successfully processed changes in ${repo}"
            fi
        done

        sleep "${interval}"
    done
}

# Auto-commit with AI-enhanced message
function __auto_commit() {
    if ! __ensure_git_repo; then
        return 1
    }

    if ! __ensure_clean_workspace; then
        return 2
    }

    local message="${1:-}"
    if [[ -z "${message}" ]]; then
        if ! message=$(__generate_commit_message); then
            return 4
        fi
    fi

    if ! git add -A; then
        __handle_error 14 "Failed to stage changes" "auto_commit"
        return 14
    }

    if ! git commit -m "${message}"; then
        __handle_error 15 "Failed to commit changes" "auto_commit"
        return 15
    }

    __log "INFO" "Auto-committed changes with message: ${message}"
    return 0
}

# Auto-push with security checks
function __auto_push() {
    if ! __ensure_git_repo; then
        return 1
    }

    if __ensure_command "gitleaks"; then
        if ! gitleaks detect --no-git; then
            __handle_error 16 "Security check failed" "auto_push"
            return 16
        fi
    fi

    if ! git push; then
        __handle_error 17 "Failed to push changes" "auto_push"
        return 17
    }

    __log "INFO" "Auto-pushed changes"
    return 0
}

# Create PR with AI-enhanced title
function __auto_pr() {
    if ! __ensure_git_repo; then
        return 1
    }

    if ! __ensure_command "gh"; then
        return 3
    }

    local description="$1"
    if [[ -z "${description}" ]]; then
        __handle_error 18 "No PR description provided" "auto_pr"
        return 18
    }

    local branch="feature/$(echo "${description}" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]-' | tr ' ' '-')"

    if ! git checkout -b "${branch}"; then
        __handle_error 19 "Failed to create branch" "auto_pr"
        return 19
    }

    if ! __auto_commit "feat: ${description}"; then
        __handle_error 20 "Failed to commit changes" "auto_pr"
        return 20
    }

    if ! __auto_push; then
        __handle_error 21 "Failed to push changes" "auto_pr"
        return 21
    }

    if ! gh pr create --title "${description}" --draft; then
        __handle_error 22 "Failed to create PR" "auto_pr"
        return 22
    }

    __log "INFO" "Created PR: ${description}"
    return 0
# Register functions
autoload -Uz commit_message workspace_init workspace_scan workspace_monitor
