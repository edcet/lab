#!/bin/zsh

# System Gateway: Human-Centric Resource Management
# Designed for clarity, control, and growth

# Enable extended globbing for pattern matching
setopt EXTENDED_GLOB

# Make functions available
autoload -Uz system_help system_status system_reset system_sync
autoload -Uz envinfo envhelp envset envsync
autoload -Uz gac gap gapr gwi githelp

# System-wide integration points
typeset -gA __system_integrations=()
typeset -gA __system_states=()
typeset -gA __system_capabilities=()

# Initialize resource arrays with human-centric priorities
typeset -gA env_vars=()
typeset -gA file_handlers=()
typeset -gA help_topics=()
typeset -ga resource_priorities=(
    'essential'   # Core system needs
    'protective'  # Security and safety
    'productive'  # Development tools
    'supportive'  # Workflow enhancers
    'preferential' # User customizations
)

# Progressive discovery system with learning paths
typeset -gA feature_levels=(
    'beginner'    'Essential operations'
    'regular'     'Common workflows'
    'advanced'    'Power user features'
    'expert'      'System internals'
)

# After feature_levels definition
typeset -gA __user_progress
typeset -gA __feature_usage

# After initialization checks
typeset -g SYSTEM_SAFE_MODE=0

# Enhanced safety system
function __ensure_safety() {
    local operation="$1"
    local fallback="$2"
    local critical="${3:-0}"

    if (( $? != 0 )) || [[ "$SYSTEM_SAFE_MODE" == "1" ]]; then
        __system_log WARN "Operation failed: $operation"
        [[ -n "$fallback" ]] && eval "$fallback"
        (( critical )) && SYSTEM_SAFE_MODE=1
        return 1
    fi
    return 0
}

# Enhanced logging with timestamps and context
function __system_log() {
    local level="$1"
    shift
    local msg="$*"
    local ts=$(date '+%Y-%m-%d %H:%M:%S')
    local context="${funcstack[3]:-system}"

    # Ensure log directory exists
    local log_dir="${XDG_STATE_HOME:-$HOME/.local/state}/system_gateway"
    mkdir -p "$log_dir"

    # Log rotation
    local log_file="$log_dir/system.log"
    if [[ -f "$log_file" ]] && [[ $(stat -f%z "$log_file") -gt 10485760 ]]; then
        mv "$log_file" "$log_file.old"
    fi

    echo "[$ts] [$level] [$context] $msg" >> "$log_file"

    # Terminal output with color
    case "$level" in
        ERROR) print -P "%F{red}Error:%f $msg" >&2 ;;
        WARN)  print -P "%F{yellow}Warning:%f $msg" >&2 ;;
        INFO)  print -P "%F{blue}Info:%f $msg" ;;
        DEBUG) [[ -n "$SYSTEM_DEBUG" ]] && print -P "%F{cyan}Debug:%f $msg" ;;
    esac
}

# Adaptive learning path tracking
function __track_feature_usage() {
    local feature="$1"
    local level="${2:-regular}"

    # Skip if in safe mode
    [[ "$SYSTEM_SAFE_MODE" == "1" ]] && return 0

    # Validate feature
    if [[ -z "${__system_capabilities[(r)*$feature*]}" ]]; then
        __system_log DEBUG "Unknown feature: $feature"
        return 0
    fi

    # Safe increment
    __feature_usage[$feature]=$(( ${__feature_usage[$feature]:-0} + 1 ))

    # Save state periodically
    if (( ${__feature_usage[$feature]} % 5 == 0 )); then
        __save_feature_usage || __system_log WARN "Failed to save usage stats"
    fi
}

# Intelligent progression suggestions
function __suggest_progression() {
    local current_level="${SYSTEM_EXPERTISE:-beginner}"
    local next_level

    case "$current_level" in
        beginner) next_level="regular" ;;
        regular)  next_level="advanced" ;;
        advanced) next_level="expert" ;;
        expert)   return 0 ;;
    esac

    print -P "\n%F{blue}Growth Opportunity:%f"
    print -P "You've been using ${current_level} features effectively."
    print -P "Ready to explore %F{green}${next_level}%f capabilities?"
    print -P "  Run: %F{yellow}system_help progression ${next_level}%f"
}

# Cross-component registration
function register_integration() {
    local component="$1"
    local capabilities="$2"
    local state_handler="$3"

    # Validate inputs
    if [[ -z "$component" || -z "$capabilities" ]]; then
        __system_log ERROR "Invalid registration: $component"
        return 1
    fi

    # Clean capabilities
    capabilities=$(echo "$capabilities" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

    # Backup existing registration
    if [[ -n "${__system_integrations[$component]}" ]]; then
        __system_log INFO "Updating existing component: $component"
    fi

    # Safe registration
    __system_integrations[$component]="$capabilities"
    __system_states[$component]="$state_handler"

    # Process capabilities into array
    local -a cap_array
    while IFS= read -r line; do
        [[ -n "$line" ]] && cap_array+=("$line")
    done <<< "$capabilities"

    __system_capabilities[$component]="${(j:,:)cap_array}"

    # Verify registration
    if [[ -z "${__system_integrations[$component]}" ]]; then
        __system_log ERROR "Registration failed: $component"
        return 1
    fi

    __system_log INFO "Registered component: $component"
    return 0
}

# Proactive system monitoring
function __monitor_system_health() {
    local issues=()
    local warnings=()
    local suggestions=()

    # Check component health
    for component state_handler in ${(kv)__system_states}; do
        if ! eval "$state_handler" >/dev/null 2>&1; then
            issues+=("$component: state check failed")
            suggestions+=("Try 'system_help $component' for troubleshooting")
        fi
    done

    # Check integration points
    for component capabilities in ${(kv)__system_integrations}; do
        for capability in ${(f)capabilities}; do
            if ! command -v "${capability%% *}" >/dev/null 2>&1; then
                warnings+=("$component: missing capability - ${capability%% *}")
            fi
        done
    done

    # Verify environment consistency
    if ! __verify_environment_consistency; then
        warnings+=("Environment state may be inconsistent")
        suggestions+=("Run 'envmgr sync' to reconcile state")
    fi

    # Report status
    if (( ${#issues} > 0 )); then
        print -P "%F{red}Critical Issues:%f"
        for issue in $issues; do
            print -P "%F{red}  ⚠️  $issue%f"
        done
    fi

    if (( ${#warnings} > 0 )); then
        print -P "%F{yellow}Warnings:%f"
        for warning in $warnings; do
            print -P "%F{yellow}  ⚠️  $warning%f"
        done
    fi

    if (( ${#suggestions} > 0 )); then
        print -P "%F{blue}Suggestions:%f"
        for suggestion in $suggestions; do
            print -P "%F{blue}  💡 $suggestion%f"
        done
    fi

    return $(( ${#issues} > 0 ))
}

# Environment consistency check
function __verify_environment_consistency() {
    local issues=0

    # Essential directory check
    for dir in "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME"; do
        if [[ ! -d "$dir" ]]; then
            __system_log WARN "Missing directory: $dir"
            mkdir -p "$dir" || ((issues++))
        fi
    done

    # State file integrity
    if [[ -f "$ENVMGR_STATE_FILE" ]]; then
        local temp_state
        source "$ENVMGR_STATE_FILE" 2>/dev/null || {
            __system_log ERROR "Corrupted state file"
            mv "$ENVMGR_STATE_FILE" "$ENVMGR_STATE_FILE.broken"
            ((issues++))
        }
    fi

    # Tool availability
    for tool in git python node mise; do
        if ! command -v $tool >/dev/null 2>&1; then
            __system_log WARN "Optional tool not available: $tool"
        fi
    done

    return $issues
}

# Enhanced help system with context awareness
function system_help() {
    local topic="${1:-overview}"
    local detail="${2:-basic}"
    local context="${3:-current}"

    case "$topic" in
        overview)
            print -P "%F{blue}System Overview%f"
            print -P "%F{cyan}Active Components:%f"
            for component capabilities in ${(kv)__system_capabilities}; do
                print -P "%F{green}$component:%f"
                print -P "${(f)capabilities}" | sed 's/^/  /'
            done

            if [[ "$detail" == "detailed" ]]; then
                print -P "\n%F{blue}System Health:%f"
                __monitor_system_health

                print -P "\n%F{blue}Environment State:%f"
                envinfo detailed
            fi
            ;;
        health)
            __monitor_system_health
            ;;
        integrations)
            print -P "%F{blue}System Integrations:%f"
            for component capabilities in ${(kv)__system_integrations}; do
                print -P "%F{yellow}$component:%f"
                print -P "${(f)capabilities}" | sed 's/^/  /'
            done
            ;;
        state)
            print -P "%F{blue}System State:%f"
            for component state_handler in ${(kv)__system_states}; do
                print -P "%F{yellow}$component:%f"
                eval "$state_handler" | sed 's/^/  /'
            done
            ;;
        progression)
            local target_level="${2:-${SYSTEM_EXPERTISE:-beginner}}"
            print -P "%F{blue}Learning Path: ${target_level}%f"

            # Show available features
            print -P "\n%F{cyan}Available Features:%f"
            for component capabilities in ${(kv)__system_capabilities}; do
                local level="${__system_states[$component]##*:}"
                if [[ "$level" == "$target_level" ]]; then
                    print -P "%F{green}$component:%f"
                    print -P "${(f)capabilities}" | sed 's/^/  /'
                fi
            done

            # Show usage statistics
            print -P "\n%F{cyan}Your Progress:%f"
            for feature usage in ${(kv)__feature_usage}; do
                print -P "  %-20s: %d uses" "$feature" "$usage"
            done

            # Suggest next steps
            print -P "\n%F{cyan}Suggested Next Steps:%f"
            case "$target_level" in
                regular)
                    print -P "  1. Explore environment management with 'envset'"
                    print -P "  2. Try automatic git features with 'gac'"
                    print -P "  3. Learn about system health with 'system_help health'"
                    ;;
                advanced)
                    print -P "  1. Master state preservation with snapshots"
                    print -P "  2. Explore custom git hooks and PR automation"
                    print -P "  3. Learn about system integration points"
                    ;;
                expert)
                    print -P "  1. Create custom automation scripts"
                    print -P "  2. Extend the system with new components"
                    print -P "  3. Contribute to system improvement"
                    ;;
            esac
            ;;
        *)
            if [[ -n "${__system_capabilities[$topic]}" ]]; then
                print -P "%F{blue}$topic Help:%f"
                print -P "${(f)__system_capabilities[$topic]}" | sed 's/^/  /'
                eval "${__system_states[$topic]}" | sed 's/^/  /'
            else
                print -P "%F{red}Unknown topic: $topic%f"
                print -P "Try: overview, health, integrations, state, progression"
                print -P "Or one of: ${(k)__system_capabilities}"
            fi
            ;;
    esac
}

# Resource management with human context
function register_env() {
    local priority="$1"
    local name="$2"
    local value="$3"
    local description="$4"
    local help_text="${5:-$description}"
    local level="${6:-regular}"

    # Validate priority
    if [[ -z "${resource_priorities[(r)$priority]}" ]]; then
        __system_log ERROR "Invalid priority: $priority"
        return 1
    fi

    # Validate level
    if [[ -z "${feature_levels[$level]}" ]]; then
        __system_log ERROR "Invalid level: $level"
        return 1
    fi

    # Store with validation
    if [[ -n "$name" && -n "$value" ]]; then
        env_vars[$name]="$priority:$value:$description:$level"
        help_topics[$name]="$help_text"
        __system_log DEBUG "Registered env: $name ($priority)"
        return 0
    fi

    __system_log ERROR "Invalid environment registration"
    return 1
}

function register_file() {
    local priority="$1"
    local path="$2"
    local handler="$3"
    local description="$4"
    local help_text="${5:-$description}"
    local level="${6:-regular}"

    file_handlers[$path]="$priority:$handler:$description:$level"
    help_topics[$path]="$help_text"
}

# Apply environment with user awareness
function apply_env() {
    local current_priority
    local user_level="${SYSTEM_EXPERTISE:-regular}"

    for current_priority in $resource_priorities; do
        for key value in ${(kv)env_vars}; do
            local priority="${value%%:*}"
            if [[ "$priority" == "$current_priority" ]]; then
                local actual_value="${${value#*:}%%:*}"
                local description="${${value#*:*:}%%:*}"
                local level="${value##*:}"

                # Only apply if matches user's expertise level
                if [[ "$level" == "$user_level" || "$level" == "beginner" || "$priority" == "essential" ]]; then
                    export "$key=$actual_value"
                    [[ -n "$SYSTEM_DEBUG" ]] && echo "Setting $key ($priority): $description"
                fi
            fi
        done
    done
}

# Rich help system for progressive learning
function explain() {
    local topic="$1"
    local detail_level="${2:-basic}"

    if [[ -n "${help_topics[$topic]}" ]]; then
        local help_text="${help_topics[$topic]}"
        case "$detail_level" in
            basic)
                echo "\033[1;32m${topic}:\033[0m ${help_text%%.*}."
                ;;
            detailed)
                echo "\033[1;32m${topic}:\033[0m $help_text"
                if [[ -n "${env_vars[$topic]}" ]]; then
                    local value="${env_vars[$topic]}"
                    local priority="${value%%:*}"
                    echo "\033[1;34mPriority:\033[0m $priority"
                    echo "\033[1;34mCurrent Value:\033[0m ${${value#*:}%%:*}"
                fi
                ;;
            examples)
                echo "\033[1;32m${topic} Examples:\033[0m"
                # Future: Add example usage
                ;;
        esac
    else
        echo "\033[1;31mNo help available for: $topic\033[0m"
    fi
}

# Enhanced resource viewer with learning paths
function resources() {
    local view_level="${1:-current}"
    echo "\033[1;37mSystem Resources by Priority Level\033[0m"

    case "$view_level" in
        current)
            local user_level="${SYSTEM_EXPERTISE:-regular}"
            echo "\033[1;36mShowing resources for $user_level level\033[0m"
            ;;
        all)
            echo "\033[1;36mShowing all resource levels\033[0m"
            ;;
        progression)
            echo "\033[1;36mShowing learning progression\033[0m"
            ;;
    esac

    for priority in $resource_priorities; do
        echo "\n\033[1;33m${(U)priority} Priority:\033[0m"

        # Environment Variables
        echo "\033[1;34mEnvironment Variables:\033[0m"
        for key value in ${(kv)env_vars}; do
            local var_priority="${value%%:*}"
            if [[ "$var_priority" == "$priority" ]]; then
                local actual_value="${${value#*:}%%:*}"
                local description="${${value#*:*:}%%:*}"
                local level="${value##*:}"

                if [[ "$view_level" == "all" ||
                      "$view_level" == "progression" ||
                      ( "$view_level" == "current" &&
                        ( "$level" == "${SYSTEM_EXPERTISE:-regular}" ||
                          "$level" == "beginner" ||
                          "$priority" == "essential" ) ) ]]; then
                    printf "  %-20s = %-20s (%s) [%s]\n" \
                           "$key" "$actual_value" "$description" "$level"
                fi
            fi
        done

        # File Handlers
        echo "\033[1;36mFile Handlers:\033[0m"
        for path handler in ${(kv)file_handlers}; do
            local handler_priority="${handler%%:*}"
            if [[ "$handler_priority" == "$priority" ]]; then
                local actual_handler="${${handler#*:}%%:*}"
                local description="${${handler#*:*:}%%:*}"
                local level="${handler##*:}"

                if [[ "$view_level" == "all" ||
                      "$view_level" == "progression" ||
                      ( "$view_level" == "current" &&
                        ( "$level" == "${SYSTEM_EXPERTISE:-regular}" ||
                          "$level" == "beginner" ||
                          "$priority" == "essential" ) ) ]]; then
                    printf "  %-20s -> %-20s (%s) [%s]\n" \
                           "$path" "$actual_handler" "$description" "$level"
                fi
            fi
        done
    done

    if [[ "$view_level" == "progression" ]]; then
        echo "\n\033[1;35mLearning Progression:\033[0m"
        for level in ${(k)feature_levels}; do
            echo "\033[1;33m$level:\033[0m"
            # Future: Add progression guidance
        done
    fi
}

# State persistence
function __save_feature_usage() {
    local state_file="${XDG_STATE_HOME:-$HOME/.local/state}/system_gateway/feature_usage"
    mkdir -p "${state_file:h}"

    # Safe save with backup
    if [[ -f "$state_file" ]]; then
        cp "$state_file" "$state_file.bak"
    fi

    # Store state
    {
        for feature usage in ${(kv)__feature_usage}; do
            echo "$feature=$usage"
        done
    } > "$state_file.new"

    # Atomic replace
    mv "$state_file.new" "$state_file"
}

# Load saved state
function __load_feature_usage() {
    local state_file="${XDG_STATE_HOME:-$HOME/.local/state}/system_gateway/feature_usage"

    if [[ -f "$state_file" ]]; then
        while IFS='=' read -r feature usage; do
            __feature_usage[$feature]=$usage
        done < "$state_file"
    fi
}

# Add robust error handling
function __handle_error() {
    local err=$?
    local cmd="$1"
    local context="$2"

    if (( err != 0 )); then
        __system_log ERROR "Failed: $cmd in $context (error $err)"
        if [[ "$SYSTEM_SAFE_MODE" != "1" ]]; then
            __system_log WARN "Enabling safe mode"
            SYSTEM_SAFE_MODE=1
        fi
        return $err
    fi
    return 0
}

# Add system recovery
function __attempt_recovery() {
    __system_log INFO "Attempting system recovery"

    # Backup current state
    local backup_dir="${XDG_BACKUP_HOME:-$HOME/.local/backup}/system_gateway/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # Save current state
    {
        declare -p __feature_usage
        declare -p __system_integrations
        declare -p __system_states
        declare -p __system_capabilities
        declare -p env_vars
        declare -p help_topics
    } > "$backup_dir/state.zsh"

    # Check essential directories
    for dir in "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME"; do
        [[ ! -d "$dir" ]] && mkdir -p "$dir"
    done

    # Check state files
    local state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/system_gateway"
    [[ ! -d "$state_dir" ]] && mkdir -p "$state_dir"

    # Attempt to load backup state
    if [[ ! -f "$state_dir/feature_usage" && -f "$state_dir/feature_usage.bak" ]]; then
        cp "$state_dir/feature_usage.bak" "$state_dir/feature_usage"
    fi

    # Reset if needed
    if [[ "$SYSTEM_SAFE_MODE" == "1" ]]; then
        __feature_usage=()
        __system_integrations=()
        __system_states=()
        __system_capabilities=()
        __system_log INFO "Reset to clean state"

        # Re-register core components
        register_integration "system" "system_help system_status system_reset system_sync resources explain" "__check_system"
    fi

    __system_log INFO "Recovery complete. Backup at: $backup_dir"
    return 0
}

# Add periodic health check
function __periodic_health_check() {
    # Run every 5 minutes
    if (( EPOCHSECONDS - ${__last_health_check:-0} > 300 )); then
        __protect_system
        __last_health_check=$EPOCHSECONDS
    fi
}

# Hook into command execution for health monitoring
preexec() {
    local cmd="$1"
    local main_cmd="${${cmd%%[[:space:]]*}:t}"

    # Track feature usage if it's a system command
    if [[ -n "${__system_capabilities[(r)*$main_cmd*]}" ]]; then
        __track_feature_usage "$main_cmd"
    fi

    # Periodic health check
    __periodic_health_check
}

# Add proactive protection
function __protect_system() {
    # Monitor system resources
    local mem_usage=$(ps -o rss= -p $$)
    if (( mem_usage > 1000000 )); then  # 1GB
        __system_log WARN "High memory usage detected"
        __attempt_recovery
    fi

    # Check disk space
    local disk_space=$(df -k . | awk 'NR==2 {print $4}')
    if (( disk_space < 1000000 )); then  # 1GB
        __system_log WARN "Low disk space detected"
    fi

    # Monitor file descriptors
    local fd_count=$(lsof -p $$ | wc -l)
    if (( fd_count > 1000 )); then
        __system_log WARN "High file descriptor usage"
        __attempt_recovery
    fi

    return 0
}

# Enhanced initialization
{
    # Set up error handling
    setopt ERR_EXIT
    setopt PIPE_FAIL

    # Initialize core
    __load_feature_usage || __handle_error "load_feature_usage" "init"
    __verify_environment_consistency || __handle_error "verify_environment" "init"
    __protect_system || __handle_error "protect_system" "init"

    # Recovery if needed
    if [[ "$SYSTEM_SAFE_MODE" == "1" ]]; then
        __attempt_recovery
    fi

    # Register core components with proper capabilities and state checks
    register_integration "system" "system_help system_status system_reset system_sync resources explain" "__check_system"

    register_integration "git_autobuilder" "gac gap gapr gwi githelp" "__check_git_autobuilder"

    register_integration "env_manager" "envhelp envinfo envset envsync" "__check_env_manager"

} always {
    # Reset error handling
    setopt NO_ERR_EXIT
    setopt NO_PIPE_FAIL

    if [[ "$SYSTEM_SAFE_MODE" == "1" ]]; then
        __system_log WARN "System running in safe mode"
        print -P "%F{yellow}⚠️  System running in safe mode - some features disabled%f"
        print -P "Run 'system_help recovery' for assistance"
    fi
}

# Register environment variables with fixed levels
register_env 'essential' 'XDG_CONFIG_HOME' "$HOME/.config" \
    'XDG base directory specification' \
    'Standardized configuration location. Essential for system organization and tool compatibility.' \
    'beginner'

register_env 'protective' 'GNUPGHOME' "$XDG_CONFIG_HOME/gnupg" \
    'GnuPG home directory' \
    'Secure storage for encryption keys and configurations. Critical for system security.' \
    'beginner'

register_env 'productive' 'VIRTUAL_ENV' '.venv' \
    'Python virtual environment' \
    'Isolated Python environment for project dependencies. Prevents conflicts between projects.' \
    'beginner'

register_env 'supportive' 'PYTHONPATH' 'src' \
    'Python module search path' \
    'Custom module location for development. Helps Python find your project modules.' \
    'regular'

register_env 'preferential' 'EDITOR' 'code' \
    'Preferred text editor' \
    'Your chosen editor for text files. Customize this to match your workflow.' \
    'beginner'

# Initialize the environment
apply_env

# Initialize with health check
__monitor_system_health
if [[ $? -eq 0 ]]; then
    print -P "%F{green}System Gateway: All components healthy%f"
else
    print -P "%F{yellow}System Gateway: Some components need attention%f"
    print -P "%F{blue}Run 'system_help health' for details%f"
fi

# Hook into command execution for tracking
preexec() {
    local cmd="$1"
    local main_cmd="${${cmd%%[[:space:]]*}:t}"

    # Track feature usage if it's a system command
    if [[ -n "${__system_capabilities[(r)*$main_cmd*]}" ]]; then
        __track_feature_usage "$main_cmd"
    fi
}

# Add core system functions
function system_status() {
    print -P "%F{blue}System Status:%f"
    __monitor_system_health
    envinfo detailed
}

function system_reset() {
    print -P "%F{blue}Resetting system state%f"
    local backup_dir="${XDG_BACKUP_HOME:-$HOME/.local/backup}/system_gateway/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # Backup current state
    cp -r "${XDG_STATE_HOME:-$HOME/.local/state}/system_gateway" "$backup_dir/"

    # Reset state
    __feature_usage=()
    __system_integrations=()
    __system_states=()
    __system_capabilities=()

    print -P "%F{green}System reset complete. Backup at: $backup_dir%f"
}

function system_sync() {
    print -P "%F{blue}Syncing system state%f"
    __save_feature_usage
    __verify_environment_consistency
    envinfo detailed
}

# Environment information display
function envinfo() {
    local detail="${1:-basic}"
    print -P "%F{blue}Environment Information:%f"

    if [[ "$detail" == "detailed" ]]; then
        print -P "%F{cyan}Environment Details:%f"
        print -P "  Virtual Environment: ${VIRTUAL_ENV:t}"
        print -P "  Python Path: ${PYTHONPATH:-not set}"
        print -P "  Project Type: ${PROJECT_TYPE:-unknown}"
        print -P "  Tool Versions:"
        print -P "    Python: $(python --version 2>/dev/null)"
        print -P "    Node: $(node --version 2>/dev/null)"
        print -P "    Git: $(git --version 2>/dev/null)"
    else
        print -P "  Active Environment: ${VIRTUAL_ENV:t}"
        print -P "  Python: $(python --version 2>/dev/null)"
    fi
}

# Environment help system
function envhelp() {
    print -P "%F{blue}Environment Manager Help:%f"
    print -P "%F{cyan}Available Commands:%f"
    print -P "  envinfo [basic|detailed] - Show environment information"
    print -P "  envset [python|node|general] - Set up environment"
    print -P "  envsync - Sync environment state"
    print -P "  envhelp - Show this help"
}

# Environment setup
function envset() {
    local env_type="${1:-python}"
    print -P "%F{blue}Setting up $env_type environment%f"

    case "$env_type" in
        python)
            python -m venv .venv
            source .venv/bin/activate
            ;;
        node)
            mise use node@latest
            ;;
        general)
            mise use
            ;;
    esac

    envsync
}

# Environment sync
function envsync() {
    print -P "%F{blue}Syncing environment state%f"
    __verify_environment_consistency
}

# Git Autobuilder Functions
function gac() {
    local message="$1"
    print -P "%F{blue}Auto-committing changes%f"

    if [[ -z "$message" ]]; then
        message="$(git diff --cached --name-only | head -n1)"
        message="update: ${message:t}"
    fi

    git add -A
    git commit -m "$message"
}

function gap() {
    print -P "%F{blue}Auto-pushing changes%f"
    local branch="$(git rev-parse --abbrev-ref HEAD)"
    git push origin "$branch"
}

function gapr() {
    local title="$1"
    local body="$2"
    print -P "%F{blue}Creating pull request%f"

    if [[ -z "$title" ]]; then
        title="$(git log -1 --pretty=%B)"
    fi

    gh pr create --title "$title" ${body:+--body "$body"}
}

function gwi() {
    local name="${1:-${PWD:t}}"
    print -P "%F{blue}Initializing workspace: $name%f"

    # Create structure
    mkdir -p src tests docs
    touch README.md

    # Initialize git
    git init
    git add -A
    git commit -m "init: Create project structure"
}

function githelp() {
    print -P "%F{blue}Git Autobuilder Help:%f"
    print -P "%F{cyan}Available Commands:%f"
    print -P "  gac [message] - Auto-commit changes"
    print -P "  gap - Auto-push to remote"
    print -P "  gapr [title] [body] - Create pull request"
    print -P "  gwi [name] - Initialize workspace"
    print -P "  githelp - Show this help"
}

# Enhanced state checks
function __check_git_autobuilder() {
    command -v git >/dev/null 2>&1 || return 1
    [[ -n "$__system_capabilities[git_autobuilder]" ]] || return 1
    return 0
}

function __check_env_manager() {
    [[ -n "$__system_capabilities[env_manager]" ]] || return 1
    return 0
}

function __check_system() {
    [[ -n "$__system_capabilities[system]" ]] || return 1
    return 0
}
