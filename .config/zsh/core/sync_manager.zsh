#!/bin/zsh

# Sync Manager
# Handles automated git operations and cross-platform synchronization

# Guard against double-loading
if [[ -n "$__SYNC_LOADED" ]]; then
    return 0
fi
__SYNC_LOADED=1

# Use system gateway for configuration
sysgate env_set SYNC_CONFIG_DIR "${XDG_CONFIG_HOME:-$HOME/.config}/sync-manager" permanent
sysgate env_set SYNC_CACHE_DIR "${XDG_CACHE_HOME:-$HOME/.cache}/sync-manager" permanent
sysgate env_set SYNC_DATA_DIR "${XDG_DATA_HOME:-$HOME/.local/share}/sync-manager" permanent

# Ensure directories exist through system gateway
sysgate fs_mkdir "$SYNC_CONFIG_DIR"
sysgate fs_mkdir "$SYNC_CACHE_DIR"
sysgate fs_mkdir "$SYNC_DATA_DIR"

# Git operation patterns
typeset -A __SYNC_GIT_PATTERNS=(
    [config]="^\.config/.*$"
    [dotfile]="^\.[a-zA-Z0-9_-]+$"
    [system]="^(etc|usr/local)/.*$"
    [project]="^(src|lib|test)/.*$"
    [doc]="^(docs|README|LICENSE).*$"
)

# Sync strategies
typeset -A __SYNC_STRATEGIES=(
    [git]="git_sync"
    [rsync]="rsync_sync"
    [cloud]="cloud_sync"
)

# Platform-specific paths
typeset -A __SYNC_PLATFORM_PATHS=(
    [darwin]="$HOME/Library/Application Support"
    [linux]="$HOME/.config"
    [windows]="$APPDATA"
)

# Enhanced git operations with semantic commits
function __sync_git_commit() {
    local dir="$1"

    cd "$dir" || return 1

    # Process config files
    if git ls-files -mo .config/ 2>/dev/null | grep -q .; then
        git add .config/
        git commit -m "auto(config): automated update for config files"
    fi

    # Process dotfiles
    if git ls-files -mo .[^.]* 2>/dev/null | grep -v '^\.config/' | grep -q .; then
        git ls-files -mo .[^.]* | grep -v '^\.config/' | xargs git add
        git commit -m "auto(dotfile): automated update for dotfiles"
    fi

    # Process system files
    if git ls-files -mo etc/ usr/local/ 2>/dev/null | grep -q .; then
        git add etc/ usr/local/
        git commit -m "auto(system): automated update for system files"
    fi

    # Process project files
    if git ls-files -mo 'src/' 'lib/' 'test/' 2>/dev/null | grep -q .; then
        git add src/ lib/ test/
        git commit -m "auto(project): automated update for project files"
    fi

    # Process documentation
    if git ls-files -mo 'docs/' 'README*' 'LICENSE*' 2>/dev/null | grep -q .; then
        git add docs/ README* LICENSE*
        git commit -m "auto(doc): automated update for documentation"
    fi

    # Process remaining files
    if git status --porcelain | grep -v '^[MADRCU]' | grep -v '^.[MADRCU]' | grep -q .; then
        git add .
        git commit -m "auto(other): automated update for miscellaneous files"
    fi
}

# Intelligent git sync with conflict resolution
function __sync_git_sync() {
    local dir="$1"
    local remote="$2"
    local branch="$3"

    cd "$dir" || return 1

    # Store current state
    local state_hash=$(git rev-parse HEAD)

    # Pull with rebase
    if ! git pull --rebase "$remote" "$branch"; then
        # Handle conflicts
        local conflicts=($(git diff --name-only --diff-filter=U))
        for file in $conflicts; do
            for key in ${(k)__SYNC_GIT_PATTERNS}; do
                local pattern="$key"
                local category="${__SYNC_GIT_PATTERNS[$key]}"
                if [[ "$file" =~ $pattern ]]; then
                    __sync_resolve_conflict "$file" "$category"
                fi
            done
        done
    fi

    # Push changes
    git push "$remote" "$branch"
}

# Smart conflict resolution
function __sync_resolve_conflict() {
    local file="$1"
    local category="$2"

    case "$category" in
        config)
            # Keep local config but backup remote
            git checkout --ours "$file"
            git checkout --theirs "$file.remote"
            ;;
        dotfile)
            # Merge changes with backup
            if command -v meld >/dev/null 2>&1; then
                meld "$file"
            else
                git checkout --ours "$file"
                git checkout --theirs "$file.remote"
            fi
            ;;
        system)
            # Use remote for system files
            git checkout --theirs "$file"
            ;;
        *)
            # Default to manual resolution
            print -P "%F{yellow}Manual resolution required for $file%f"
            return 1
            ;;
    esac

    git add "$file"
}

# Cross-platform configuration sync
function __sync_platform_config() {
    local platform=$(uname -s | tr '[:upper:]' '[:lower:]')
    local config_dir="$1"

    # Get platform-specific path
    local target_dir="${__SYNC_PLATFORM_PATHS[$platform]}"
    if [[ -z "$target_dir" ]]; then
        print -P "%F{red}Error: Unsupported platform: $platform%f"
        return 1
    fi

    # Process each config file
    for config in $config_dir/**/*(N); do
        if [[ -f "$config" ]]; then
            local rel_path="${config#$config_dir/}"
            local target="$target_dir/$rel_path"

            # Create target directory
            mkdir -p "${target:h}"

            # Copy with platform-specific processing
            case "$platform" in
                darwin)
                    # Handle macOS specific paths
                    sed 's|$HOME|'"$HOME"'|g' "$config" > "$target"
                    ;;
                linux)
                    # Handle Linux specific paths
                    sed 's|$HOME|'"$HOME"'|g' "$config" > "$target"
                    ;;
                windows)
                    # Handle Windows specific paths
                    sed 's|$HOME|%USERPROFILE%|g' "$config" > "$target"
                    ;;
            esac

            # Set permissions
            chmod 644 "$target"
        fi
    done
}

# Automated sync orchestration
function __sync_orchestrate() {
    local -a active_channels

    # Read sync configuration
    local config_file="$SYNC_CONFIG_DIR/sync.toml"
    if [[ ! -f "$config_file" ]]; then
        print -P "%F{red}Error: Missing sync configuration%f"
        return 1
    fi

    # Process each sync channel
    while IFS= read -r line; do
        if [[ "$line" =~ '^[[:space:]]*\[\[(sync)\]\]' ]]; then
            local source target strategy
            while IFS= read -r subline; do
                case "$subline" in
                    *source*)
                        source="${subline#*=}"
                        source="${source//\"/}"
                        ;;
                    *target*)
                        target="${subline#*=}"
                        target="${target//\"/}"
                        ;;
                    *strategy*)
                        strategy="${subline#*=}"
                        strategy="${strategy//\"/}"
                        ;;
                esac
                [[ "$subline" =~ '^[[:space:]]*\[' ]] && break
            done

            if [[ -n "$source" && -n "$target" && -n "$strategy" ]]; then
                active_channels+=("$source:$target:$strategy")
            fi
        fi
    done < "$config_file"

    # Execute sync operations
    for channel in $active_channels; do
        local source="${channel%%:*}"
        local remainder="${channel#*:}"
        local target="${remainder%%:*}"
        local strategy="${remainder#*:}"

        if [[ -n "${__SYNC_STRATEGIES[$strategy]}" ]]; then
            ${__SYNC_STRATEGIES[$strategy]} "$source" "$target" &
        else
            print -P "%F{red}Error: Unknown sync strategy: $strategy%f"
        fi
    done

    wait
}

# Initialize sync manager
function __sync_init() {
    # Create default configuration if needed
    local config_file="$SYNC_CONFIG_DIR/sync.toml"
    if [[ ! -f "$config_file" ]]; then
        cat > "$config_file" <<EOL
# Sync Manager Configuration

[[sync]]
source = "$HOME/.config"
target = "git@github.com:username/dotfiles.git"
strategy = "git"
interval = 3600  # 1 hour

[[sync]]
source = "$HOME/Documents"
target = "/backup/documents"
strategy = "rsync"
interval = 86400  # 1 day

[git]
commit_interval = 300  # 5 minutes
push_interval = 3600   # 1 hour
semantic_commits = true

[rsync]
options = "--archive --verbose --delete"
exclude = [".git", ".DS_Store", "node_modules"]

[security]
encrypt_secrets = true
verify_checksums = true
EOL
    fi

    print -P "%F{green}Sync manager initialized%f"
}

# Export public interface
export -f __sync_orchestrate
