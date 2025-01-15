#!/bin/zsh

# Environment Management System v2
# Intelligent workspace management with progressive discovery

# User Experience Levels
typeset -gA __envmgr_expertise_levels=(
    'beginner'    'Essential project setup and basic environment management'
    'regular'     'Common development workflows and tool integration'
    'advanced'    'Multi-language projects and complex configurations'
    'expert'      'Custom tooling and advanced automation'
)

# Feature Categories
typeset -gA __envmgr_feature_categories=(
    'essential'   'Core environment setup and basic tools'
    'protective'  'Security and stability features'
    'productive'  'Development workflow enhancements'
    'supportive'  'Helper functions and utilities'
    'preferential' 'User customization options'
)

# Guard against double-loading and ensure clean state
if [[ -n "$__ENVMGR_LOADED" ]]; then
    return 0
fi
__ENVMGR_LOADED=1

# Rich help system
function envhelp() {
    local topic="${1:-overview}"
    local detail="${2:-basic}"

    case "$topic" in
        overview)
            print -P "%F{blue}Environment Management System%f"
            print -P "%F{cyan}Available Commands:%f"
            print -P "  envhelp [topic] [detail]  - Show help (basic|detailed|examples)"
            print -P "  envinfo                   - Show current environment"
            print -P "  envset [type] [version]   - Set up project environment"
            print -P "  envsync                   - Sync environment state"
            ;;
        expertise)
            print -P "%F{blue}Expertise Levels:%f"
            for level desc in ${(kv)__envmgr_expertise_levels}; do
                print -P "%F{yellow}$level:%f $desc"
            done
            ;;
        features)
            print -P "%F{blue}Feature Categories:%f"
            for category desc in ${(kv)__envmgr_feature_categories}; do
                print -P "%F{yellow}$category:%f $desc"
            done
            ;;
        *)
            print -P "%F{red}Unknown topic: $topic%f"
            print -P "Try: overview, expertise, features"
            ;;
    esac
}

# Enhanced environment info display
function envinfo() {
    local detail="${1:-basic}"

    print -P "%F{blue}Current Environment State:%f"
    case "$detail" in
        basic)
            [[ -n "$VIRTUAL_ENV" ]] && print -P "Python: %F{green}${VIRTUAL_ENV:t}%f"
            __envmgr_mise_available && print -P "Tools: %F{green}$(mise ls)%f"
            ;;
        detailed)
            print -P "%F{yellow}Virtual Environment:%f"
            [[ -n "$VIRTUAL_ENV" ]] && {
                print -P "  Path: $VIRTUAL_ENV"
                print -P "  Python: $(python --version 2>/dev/null)"
                print -P "  Packages: $(pip list --format=freeze | wc -l | tr -d ' ') installed"
            }

            print -P "%F{yellow}Tool Versions:%f"
            __envmgr_mise_available && mise ls --json | jq -r '.[] | "  \(.name): \(.version)"'

            print -P "%F{yellow}Project Type:%f"
            local project_type=$(__envmgr_detect_project_type "$PWD")
            print -P "  ${project_type:-Unknown}"
            ;;
        *)
            print -P "%F{red}Unknown detail level: $detail%f"
            print -P "Try: basic, detailed"
            ;;
    esac
}

# Disable correction for specific commands
nocorrect_commands=(direnv mise npm yarn pnpm go cargo ruby python java gradle mvn)
for cmd in $nocorrect_commands; do
    alias $cmd="nocorrect $cmd"
done

# Error handling
function __sync_handle_error() {
    local code=$1
    local message=$2
    local context=$3

    __envmgr_log "ERROR" "[${context}] ${message} (code: ${code})"
    return ${code}
}

function __sync_ensure_command() {
    local cmd=$1
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        __sync_handle_error 1 "Command not found: ${cmd}" "command_check"
        return 1
    fi
    return 0
}

function __sync_ensure_dir() {
    local dir=$1
    if [[ ! -d "${dir}" ]]; then
        if ! mkdir -p "${dir}"; then
            __sync_handle_error 2 "Failed to create directory: ${dir}" "directory_check"
            return 2
        fi
    fi
    return 0
}

function __sync_ensure_file() {
    local file=$1
    if [[ ! -f "${file}" ]]; then
        if ! touch "${file}"; then
            __sync_handle_error 3 "Failed to create file: ${file}" "file_check"
            return 3
        fi
    fi
    return 0
}

# Configuration
ENVMGR_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/envmgr"
ENVMGR_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/envmgr"
ENVMGR_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/envmgr"
ENVMGR_STATE_FILE="$ENVMGR_DATA_DIR/state.zsh"
ENVMGR_CONFIG_FILE="$ENVMGR_CONFIG_DIR/config.zsh"
ENVMGR_MAX_LOG_SIZE=$((10 * 1024 * 1024))  # 10MB
ENVMGR_MAX_VENV_AGE=$((30 * 24 * 60 * 60))  # 30 days
ENVMGR_MAX_VENVS=10  # Maximum number of cached environments

# Ensure directories exist
for dir in "$ENVMGR_CONFIG_DIR" "$ENVMGR_CACHE_DIR" "$ENVMGR_DATA_DIR"; do
    __sync_ensure_dir "${dir}" || return $?
done

# Enhanced logging system with rotation
function __envmgr_log() {
    local level="$1"
    shift
    local msg="$*"
    local ts=$(date '+%Y-%m-%d %H:%M:%S')
    local log_file="$ENVMGR_CACHE_DIR/envmgr.log"

    # Ensure log file exists
    __sync_ensure_file "${log_file}" || return $?

    # Rotate log if too large
    if [[ -f "$log_file" ]] && [[ $(stat -f%z "$log_file") -gt $ENVMGR_MAX_LOG_SIZE ]]; then
        if ! mv "$log_file" "$log_file.old"; then
            __sync_handle_error 4 "Failed to rotate log file" "log_rotation"
            return 4
        fi
    fi

    if ! echo "[$ts] [$level] $msg" >> "$log_file"; then
        __sync_handle_error 5 "Failed to write to log file" "logging"
        return 5
    fi

    case "$level" in
        ERROR) print -P "%F{red}Error:%f $msg" >&2 ;;
        WARN)  print -P "%F{yellow}Warning:%f $msg" >&2 ;;
        INFO)  print -P "%F{blue}Info:%f $msg" ;;
        DEBUG) [[ -n "$ENVMGR_DEBUG" ]] && print -P "%F{cyan}Debug:%f $msg" ;;
    esac
}

# Enhanced state management
typeset -A __envmgr_state
function __envmgr_save_state() {
    # Ensure state file directory exists
    __sync_ensure_dir "$(dirname "${ENVMGR_STATE_FILE}")" || return $?

    # Save state to persistent storage
    {
        echo "# Environment Manager State - $(date)"
        for key in ${(k)__envmgr_state}; do
            echo "__envmgr_state[$key]='${__envmgr_state[$key]}'"
        done
    } > "${ENVMGR_STATE_FILE}" || {
        __sync_handle_error 6 "Failed to save state" "state_management"
        return 6
    }
}

function __envmgr_load_state() {
    if [[ -f "$ENVMGR_STATE_FILE" ]]; then
        source "$ENVMGR_STATE_FILE" || {
            __sync_handle_error 7 "Failed to load state" "state_management"
            return 7
        }
    fi
}

# Initialize state
__envmgr_state[active_env]=""
__envmgr_state[previous_env]=""
__envmgr_state[last_cleanup]=$(date +%s)
__envmgr_load_state

# Safe PATH manipulation with validation
function __envmgr_path_add() {
    local new_path="$1"
    if [[ ! -d "$new_path" ]]; then
        __envmgr_log WARN "Adding non-existent path: $new_path"
        return 1
    fi
    if [[ ! :$PATH: == *":$new_path:"* ]]; then
        PATH="$new_path:$PATH"
        __envmgr_log DEBUG "Added to PATH: $new_path"
        return 0
    fi
    return 0
}

function __envmgr_path_remove() {
    local old_path="$1"
    PATH=:$PATH:
    PATH=${PATH//:$old_path:/:}
    PATH=${PATH#:}
    PATH=${PATH%:}
    __envmgr_log DEBUG "Removed from PATH: $old_path"
}

# Enhanced Mise integration with version management
function __envmgr_mise_available() {
    __sync_ensure_command "mise"
}

function __envmgr_mise_init() {
    if __envmgr_mise_available; then
        if ! mise activate zsh >/dev/null 2>&1; then
            __sync_handle_error 8 "Failed to initialize mise" "mise_init"
            return 8
        fi
        __envmgr_log INFO "mise initialized successfully"
        return 0
    fi
    return 1
}

function __envmgr_mise_use() {
    local tool="$1"
    local version="$2"
    if __envmgr_mise_available; then
        if ! mise use "$tool@${version:-latest}" >/dev/null 2>&1; then
            __sync_handle_error 9 "Failed to use $tool@${version:-latest}" "mise_use"
            return 9
        fi
        __envmgr_log INFO "Using $tool@${version:-latest}"
        return 0
    fi
    return 1
}

# Enhanced Python environment management
function __envmgr_venv_create() {
    local venv_path="$1"
    local python_version="$2"

    if [[ ! -d "$venv_path" ]]; then
        if [[ -n "$python_version" ]] && __envmgr_mise_available; then
            mise use "python@$python_version" || {
                __sync_handle_error 10 "Failed to set Python version" "venv_create"
                return 10
            }
        fi

        if ! python3 -m venv "$venv_path"; then
            __sync_handle_error 11 "Failed to create virtual environment" "venv_create"
            return 11
        fi
        __envmgr_log INFO "Created virtual environment at $venv_path"
    fi
    return 0
}

function __envmgr_venv_activate() {
    local venv_path="$1"
    if [[ -f "$venv_path/bin/activate" ]]; then
        source "$venv_path/bin/activate" || {
            __sync_handle_error 12 "Failed to activate virtual environment" "venv_activate"
            return 12
        }
        __envmgr_log INFO "Activated virtual environment at $venv_path"
        return 0
    fi
    __envmgr_log ERROR "Virtual environment not found at $venv_path"
    return 1
}

# Enhanced project type detection with more languages and frameworks
function __envmgr_detect_project_type() {
    local dir="$1"
    local type=""
    local subtype=""

    # Multi-language workspace detection
    if [[ -f "$dir/workspace.jsonc" || -f "$dir/workspace.json" ]]; then
        echo "workspace:vscode"
        return
    elif [[ -f "$dir/flake.nix" ]]; then
        echo "workspace:nix"
        return
    fi

    # Python project detection with framework awareness
    if [[ -f "$dir/pyproject.toml" ]]; then
        type="python"
        if grep -q "django" "$dir/pyproject.toml"; then
            subtype="django"
        elif grep -q "fastapi" "$dir/pyproject.toml"; then
            subtype="fastapi"
        elif grep -q "flask" "$dir/pyproject.toml"; then
            subtype="flask"
        else
            subtype="modern"
        fi
    elif [[ -f "$dir/setup.py" ]]; then
        type="python"
        subtype="legacy"
    elif [[ -f "$dir/requirements.txt" ]]; then
        type="python"
        subtype="simple"
    # Node.js with framework detection
    elif [[ -f "$dir/package.json" ]]; then
        type="node"
        if [[ -f "$dir/next.config.js" || -f "$dir/next.config.mjs" ]]; then
            subtype="next"
        elif [[ -f "$dir/nuxt.config.js" || -f "$dir/nuxt.config.ts" ]]; then
            subtype="nuxt"
        elif grep -q '"react"' "$dir/package.json"; then
            subtype="react"
        elif grep -q '"vue"' "$dir/package.json"; then
            subtype="vue"
        elif [[ -f "$dir/yarn.lock" ]]; then
            subtype="yarn"
        elif [[ -f "$dir/pnpm-lock.yaml" ]]; then
            subtype="pnpm"
        else
            subtype="npm"
        fi
    # Rust with additional metadata
    elif [[ -f "$dir/Cargo.toml" ]]; then
        type="rust"
        if [[ -d "$dir/src/bin" ]]; then
            subtype="binary"
        elif [[ -f "$dir/src/lib.rs" ]]; then
            subtype="library"
        else
            subtype="default"
        fi
    # Go with module awareness
    elif [[ -f "$dir/go.mod" ]]; then
        type="go"
        if [[ -f "$dir/main.go" ]]; then
            subtype="binary"
        elif grep -q "package main" "$dir/cmd/*/main.go" 2>/dev/null; then
            subtype="cmd"
        else
            subtype="library"
        fi
    # Ruby with framework detection
    elif [[ -f "$dir/Gemfile" ]]; then
        type="ruby"
        if [[ -f "$dir/config/application.rb" ]]; then
            subtype="rails"
        elif [[ -f "$dir/config.ru" ]]; then
            subtype="rack"
        else
            subtype="gem"
        fi
    # Java/Kotlin ecosystem
    elif [[ -f "$dir/pom.xml" ]]; then
        type="java"
        if grep -q "kotlin" "$dir/pom.xml"; then
            subtype="kotlin:maven"
        else
            subtype="maven"
        fi
    elif [[ -f "$dir/build.gradle" || -f "$dir/build.gradle.kts" ]]; then
        type="java"
        if [[ -f "$dir/build.gradle.kts" ]] || grep -q "kotlin" "$dir/build.gradle" 2>/dev/null; then
            subtype="kotlin:gradle"
        else
            subtype="gradle"
        fi
    # PHP detection
    elif [[ -f "$dir/composer.json" ]]; then
        type="php"
        if [[ -f "$dir/artisan" ]]; then
            subtype="laravel"
        elif [[ -d "$dir/wp-content" ]]; then
            subtype="wordpress"
        else
            subtype="composer"
        fi
    # Elixir detection
    elif [[ -f "$dir/mix.exs" ]]; then
        type="elixir"
        if [[ -d "$dir/lib" && -d "$dir/web" ]]; then
            subtype="phoenix"
        else
            subtype="mix"
        fi
    # Rust detection
    elif [[ -f "$dir/Cargo.toml" ]]; then
        type="rust"
        if grep -q "rocket" "$dir/Cargo.toml"; then
            subtype="rocket"
        elif grep -q "actix" "$dir/Cargo.toml"; then
            subtype="actix"
        else
            subtype="cargo"
        fi
    else
        echo "unknown"
        return
    fi

    echo "${type}:${subtype}"
}

# Enhanced cleanup with smart caching
function __envmgr_cleanup() {
    local current_time=$(date +%s)
    local cleanup_needed=0

    # Check if cleanup is needed
    if (( current_time - ${__envmgr_state[last_cleanup]:-0} >= 86400 )); then
        cleanup_needed=1
    fi

    # Count environments
    local venv_count=$(find "$ENVMGR_DATA_DIR/venvs" -maxdepth 1 -type d | wc -l)
    if (( venv_count > ENVMGR_MAX_VENVS )); then
        cleanup_needed=1
    fi

    if (( cleanup_needed == 1 )); then
        __envmgr_log INFO "Running smart environment cleanup"

        # Get all environments sorted by last access time
        local -a venv_dirs
        venv_dirs=($(find "$ENVMGR_DATA_DIR/venvs" -maxdepth 1 -type d -exec stat -f "%m %N" {} \; | sort -rn | cut -d' ' -f2-))

        # Keep track of space saved
        local space_saved=0
        local envs_removed=0

        # Process each environment
        for venv in $venv_dirs[2,-1]; do  # Skip the first one (parent dir)
            local remove=0
            local venv_age=$((current_time - $(stat -f%m "$venv")))
            local venv_size=$(du -sk "$venv" | cut -f1)

            # Check removal criteria
            if (( venv_age > ENVMGR_MAX_VENV_AGE )); then
                remove=1
            elif (( venv_count > ENVMGR_MAX_VENVS )); then
                remove=1
            elif [[ ! -f "$venv/.last_used" ]]; then
                remove=1
            fi

            # Remove if criteria met
            if (( remove == 1 )); then
                rm -rf "$venv"
                space_saved=$((space_saved + venv_size))
                envs_removed=$((envs_removed + 1))
                __envmgr_log INFO "Removed environment: $venv (${venv_size}KB)"
                venv_count=$((venv_count - 1))
            fi
        done

        # Report cleanup results
        if (( envs_removed > 0 )); then
            __envmgr_log INFO "Cleanup complete: removed $envs_removed environments, saved $((space_saved / 1024))MB"
        fi

        # Rotate logs if needed
        if [[ -f "$ENVMGR_CACHE_DIR/envmgr.log" ]]; then
            local log_size=$(stat -f%z "$ENVMGR_CACHE_DIR/envmgr.log")
            if (( log_size > ENVMGR_MAX_LOG_SIZE )); then
                mv "$ENVMGR_CACHE_DIR/envmgr.log" "$ENVMGR_CACHE_DIR/envmgr.log.old"
                __envmgr_log INFO "Rotated log file"
            fi
        fi

        __envmgr_state[last_cleanup]=$current_time
        __envmgr_save_state
    fi
}

# Enhanced environment switching with framework-specific handling
function use_env() {
    local project_dir="${1:-$PWD}"
    local project_type=$(__envmgr_detect_project_type "$project_dir")
    local project_name=${project_dir:t}
    local type=${project_type%%:*}
    local subtype=${project_type#*:}

    __envmgr_log INFO "Switching to environment for $project_name ($project_type)"

    # Save previous state
    __envmgr_state[previous_env]="${__envmgr_state[active_env]}"

    # Deactivate current environment if exists
    if [[ -n "$VIRTUAL_ENV" ]]; then
        deactivate 2>/dev/null
        __envmgr_log DEBUG "Deactivated previous virtual environment"
    fi

    # Initialize mise if available
    __envmgr_mise_init

    # Framework-specific environment setup
    case "$type" in
        python)
            local venv_path="$project_dir/.venv"
            local python_version=""
            local requirements_file=""

            # Framework-specific setup
            case "$subtype" in
                django)
                    requirements_file="requirements/local.txt"
                    [[ ! -f "$requirements_file" ]] && requirements_file="requirements.txt"
                    export DJANGO_SETTINGS_MODULE="config.settings.local"
                    ;;
                fastapi)
                    requirements_file="requirements/dev.txt"
                    [[ ! -f "$requirements_file" ]] && requirements_file="requirements.txt"
                    export FASTAPI_ENV="development"
                    ;;
                flask)
                    requirements_file="requirements/dev.txt"
                    [[ ! -f "$requirements_file" ]] && requirements_file="requirements.txt"
                    export FLASK_ENV="development"
                    export FLASK_DEBUG=1
                    ;;
            esac

            # Detect Python version
            if [[ -f "$project_dir/pyproject.toml" ]]; then
                python_version=$(grep -E '^python = ".*"' "$project_dir/pyproject.toml" 2>/dev/null | cut -d'"' -f2)
            fi

            __envmgr_venv_create "$venv_path" "$python_version"
            if __envmgr_venv_activate "$venv_path"; then
                __envmgr_state[active_env]="$venv_path"

                # Add project root to PYTHONPATH if src directory exists
                if [[ -d "$project_dir/src" ]]; then
                    export PYTHONPATH="$project_dir/src:$PYTHONPATH"
                    __envmgr_log DEBUG "Added src directory to PYTHONPATH"
                fi

                # Install dependencies if needed
                if [[ ! -f "$venv_path/.deps_installed" ]]; then
                    if [[ -n "$requirements_file" && -f "$project_dir/$requirements_file" ]]; then
                        pip install -r "$project_dir/$requirements_file"
                    elif [[ -f "$project_dir/pyproject.toml" ]]; then
                        pip install -e ".$project_dir[dev]"
                    fi
                    touch "$venv_path/.deps_installed"
                fi
            fi
            ;;
        node)
            local node_version=$(jq -r '.engines.node // "latest"' "$project_dir/package.json" 2>/dev/null)
            __envmgr_mise_use "node" "$node_version"

            # Framework-specific setup
            case "$subtype" in
                next)
                    export NODE_ENV="development"
                    [[ ! -f "node_modules/.deps_installed" ]] && {
                        npm install
                        touch "node_modules/.deps_installed"
                    }
                    ;;
                nuxt)
                    export NODE_ENV="development"
                    [[ ! -f "node_modules/.deps_installed" ]] && {
                        npm install
                        touch "node_modules/.deps_installed"
                    }
                    ;;
                react)
                    export NODE_ENV="development"
                    [[ ! -f "node_modules/.deps_installed" ]] && {
                        npm install
                        touch "node_modules/.deps_installed"
                    }
                    ;;
                vue)
                    export NODE_ENV="development"
                    [[ ! -f "node_modules/.deps_installed" ]] && {
                        npm install
                        touch "node_modules/.deps_installed"
                    }
                    ;;
                yarn)
                    [[ ! -f "node_modules/.deps_installed" ]] && {
                        yarn install
                        touch "node_modules/.deps_installed"
                    }
                    ;;
                pnpm)
                    [[ ! -f "node_modules/.deps_installed" ]] && {
                        pnpm install
                        touch "node_modules/.deps_installed"
                    }
                    ;;
                npm)
                    [[ ! -f "node_modules/.deps_installed" ]] && {
                        npm install
                        touch "node_modules/.deps_installed"
                    }
                    ;;
            esac
            ;;
        workspace)
            case "$subtype" in
                vscode)
                    # Handle VS Code workspace
                    if [[ -f "$project_dir/.vscode/settings.json" ]]; then
                        __envmgr_log INFO "Loading VS Code workspace settings"
                    fi
                    ;;
                nix)
                    # Handle Nix development environment
                    if command -v nix &>/dev/null; then
                        __envmgr_log INFO "Entering Nix development environment"
                        # TODO: Implement nix-shell or nix develop integration
                    fi
                    ;;
            esac
            ;;
        rust)
            __envmgr_mise_use "rust" "stable"
            case "$subtype" in
                rocket|actix)
                    export RUST_LOG="debug"
                    export RUST_BACKTRACE=1
                    ;;
            esac
            ;;
        go)
            __envmgr_mise_use "go" "latest"
            case "$subtype" in
                binary|cmd)
                    export GO111MODULE=on
                    export GOFLAGS="-mod=vendor"
                    ;;
                library)
                    export GO111MODULE=on
                    ;;
            esac
            ;;
        ruby)
            local ruby_version=$(grep -E '^ruby' "$project_dir/.ruby-version" 2>/dev/null || echo "latest")
            __envmgr_mise_use "ruby" "$ruby_version"
            case "$subtype" in
                rails)
                    export RAILS_ENV="development"
                    ;;
                rack)
                    export RACK_ENV="development"
                    ;;
            esac
            ;;
        java)
            local java_version
            case "$subtype" in
                *:maven)
                    java_version=$(grep -E '<java.version>' "$project_dir/pom.xml" 2>/dev/null | sed -E 's/.*<java.version>(.*)<\/java.version>.*/\1/')
                    ;;
                *:gradle)
                    java_version=$(grep -E 'sourceCompatibility' "$project_dir/build.gradle" 2>/dev/null | grep -oE '[0-9]+' || echo "latest")
                    ;;
            esac
            __envmgr_mise_use "java" "${java_version:-latest}"
            ;;
        php)
            case "$subtype" in
                laravel)
                    export APP_ENV="local"
                    export APP_DEBUG=true
                    ;;
                wordpress)
                    export WP_ENV="development"
                    export WP_DEBUG=true
                    ;;
            esac
            ;;
        elixir)
            case "$subtype" in
                phoenix)
                    export MIX_ENV="dev"
                    ;;
                mix)
                    export MIX_ENV="dev"
                    ;;
            esac
            ;;
        unknown)
            __envmgr_log WARN "Unknown project type, using default environment"
            ;;
    esac

    # Load project-specific environment if exists
    if [[ -f "$project_dir/.env" ]]; then
        set -a
        source "$project_dir/.env"
        set +a
        __envmgr_log INFO "Loaded project environment from .env"
    fi

    # Update state and mark environment as used
    touch "$ENVMGR_DATA_DIR/venvs/${project_name}/.last_used"
    __envmgr_state[current_dir]="$project_dir"
    __envmgr_save_state

    # Run cleanup if needed
    __envmgr_cleanup
}

# Auto-environment switching with debouncing
typeset -F SECONDS
__envmgr_last_switch=0
function __envmgr_auto_switch() {
    # Debounce rapid directory changes
    if (( SECONDS - __envmgr_last_switch < 1 )); then
        return
    fi

    if [[ "$PWD" != "${__envmgr_state[current_dir]}" ]]; then
        use_env "$PWD"
        __envmgr_last_switch=$SECONDS
    fi
}

# Hook into directory changes
autoload -Uz add-zsh-hook
add-zsh-hook chpwd __envmgr_auto_switch

# Enhanced utility functions
function envmgr() {
    local cmd="$1"
    shift

    case "$cmd" in
        status)
            print -P "%F{blue}Environment Manager Status:%f"
            print "Active Environment: ${__envmgr_state[active_env]:-none}"
            print "Previous Environment: ${__envmgr_state[previous_env]:-none}"
            print "Current Directory: ${__envmgr_state[current_dir]:-none}"
            print "\nEnvironment Details:"
            if [[ -n "$VIRTUAL_ENV" ]]; then
                print "Python: $(python --version 2>/dev/null)"
                print "Pip: $(pip --version 2>/dev/null)"
            fi
            if command -v node &>/dev/null; then
                print "Node: $(node --version 2>/dev/null)"
                print "NPM: $(npm --version 2>/dev/null)"
            fi
            ;;
        cleanup)
            __envmgr_cleanup
            ;;
        reload)
            __envmgr_load_state
            __envmgr_auto_switch
            ;;
        debug)
            export ENVMGR_DEBUG=1
            __envmgr_log INFO "Debug mode enabled"
            ;;
        reset)
            if [[ -n "$VIRTUAL_ENV" ]]; then
                deactivate
            fi
            __envmgr_state[active_env]=""
            __envmgr_state[current_dir]=""
            __envmgr_save_state
            __envmgr_log INFO "Environment state reset"
            ;;
        list)
            print -P "%F{blue}Available Environments:%f"
            local -a venv_dirs
            venv_dirs=($(find "$ENVMGR_DATA_DIR/venvs" -maxdepth 1 -type d -exec stat -f "%m %N" {} \; | sort -rn | cut -d' ' -f2-))
            for venv in $venv_dirs[2,-1]; do
                local last_used=$(stat -f%m "$venv")
                local age=$(( $(date +%s) - last_used ))
                local days=$(( age / 86400 ))
                print "  ${venv:t} (last used $days days ago)"
            done
            ;;
        help)
            print -P "%F{blue}Environment Manager Commands:%f"
            print "  status  - Show current environment status"
            print "  cleanup - Force cleanup of old environments"
            print "  reload  - Reload environment state"
            print "  debug   - Enable debug logging"
            print "  reset   - Reset environment state"
            print "  list    - List available environments"
            print "  help    - Show this help message"
            ;;
        *)
            print -P "%F{red}Unknown command: $cmd%f"
            envmgr help
            return 1
            ;;
    esac
}

# Initialize on shell startup
__envmgr_auto_switch

# Intelligent state preservation
function __envmgr_preserve_state() {
    local reason="$1"
    local timestamp=$(date +%s)
    local snapshot_file="$ENVMGR_DATA_DIR/snapshots/${timestamp}_${reason// /_}.zsh"

    mkdir -p "$ENVMGR_DATA_DIR/snapshots"

    # Preserve current state with metadata
    {
        echo "# Environment Snapshot - $(date)"
        echo "# Reason: $reason"
        echo "# Working Directory: $PWD"
        echo "# Active Tools: $(mise ls 2>/dev/null)"
        echo
        declare -p __envmgr_state
        echo
        echo "# Environment Variables"
        env | grep -E '^(PYTHON|NODE|RUBY|JAVA|GO|RUST|PATH|PWD|HOME|USER|SHELL|TERM)' | sort
        echo
        echo "# Tool Versions"
        mise ls 2>/dev/null
    } > "$snapshot_file"

    # Rotate old snapshots
    local -a old_snapshots
    old_snapshots=($ENVMGR_DATA_DIR/snapshots/*_*.zsh(.Nm-30))
    if (( ${#old_snapshots} > 10 )); then
        rm -f "${old_snapshots[@]:0:-10}"
    fi

    __envmgr_log INFO "State preserved: $reason"
}

# Intelligent state recovery
function __envmgr_recover_state() {
    local snapshot="${1:-latest}"
    local snapshot_file

    case "$snapshot" in
        latest)
            snapshot_file="$(\ls -t $ENVMGR_DATA_DIR/snapshots/*.zsh 2>/dev/null | head -1)"
            ;;
        list)
            print -P "%F{blue}Available Snapshots:%f"
            for snap in $ENVMGR_DATA_DIR/snapshots/*.zsh(.); do
                local reason="${${snap:t}#[0-9]*_}"
                reason="${reason%.zsh}"
                reason="${reason//_/ }"
                local date="$(stat -f '%Sm' $snap)"
                print -P "%F{yellow}$date:%f $reason"
            done
            return
            ;;
        *)
            snapshot_file="$(\ls -t $ENVMGR_DATA_DIR/snapshots/*${snapshot}*.zsh 2>/dev/null | head -1)"
            ;;
    esac

    if [[ ! -f "$snapshot_file" ]]; then
        __envmgr_log ERROR "No snapshot found: $snapshot"
        return 1
    fi

    # Load snapshot with safety checks
    local temp_state
    declare -A temp_state
    source "$snapshot_file" || {
        __envmgr_log ERROR "Failed to load snapshot: $snapshot_file"
        return 1
    }

    # Verify snapshot integrity
    if [[ -z "${temp_state[active_env]}" ]]; then
        __envmgr_log ERROR "Invalid snapshot state"
        return 1
    fi

    # Apply snapshot
    __envmgr_state=("${(@kv)temp_state}")
    __envmgr_log INFO "State recovered from: ${snapshot_file:t}"

    # Attempt to restore environment
    if [[ -n "${temp_state[active_env]}" ]]; then
        __envmgr_activate "${temp_state[active_env]}" || \
            __envmgr_log WARN "Failed to restore environment: ${temp_state[active_env]}"
    fi
}

# Automatic state preservation
function __envmgr_auto_preserve() {
    # Preserve state on significant changes
    local current_env="$(__envmgr_detect_project_type "$PWD")"
    if [[ "$current_env" != "${__envmgr_state[active_env]}" ]]; then
        __envmgr_preserve_state "Environment change: ${__envmgr_state[active_env]} -> $current_env"
    fi
}

# Register with system gateway
if typeset -f register_integration >/dev/null; then
    register_integration "env_manager" "
    envhelp - Show environment help
    envinfo - Show environment info
    envset - Set up environment
    envsync - Sync environment
    " "envinfo detailed"
fi

# Initialize with auto-preservation
__envmgr_auto_preserve
