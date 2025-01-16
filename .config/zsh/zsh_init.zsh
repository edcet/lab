#!/usr/bin/env zsh
setopt NO_UNSET NO_NULL_GLOB

# Core paths
: ${XDG_CONFIG_HOME:=$HOME/.config}
: ${XDG_CACHE_HOME:=$HOME/.cache}
: ${XDG_DATA_HOME:=$HOME/.local/share}
: ${XDG_STATE_HOME:=$HOME/.local/state}

# Ensure directories exist
mkdir -p "${XDG_CONFIG_HOME}/zsh"
mkdir -p "${XDG_CACHE_HOME}/zsh"
mkdir -p "${XDG_DATA_HOME}/zsh"
mkdir -p "${XDG_STATE_HOME}/zsh"
# Load gateway first - MUST succeed
source "$ZDOTDIR/core/system_gateway.zsh" || exit 1

# Then load everything else
source "$ZDOTDIR/core/sync_manager.zsh"
source "$ZDOTDIR/core/git_autobuilder.zsh"
source "$ZDOTDIR/core/project_bootstrap.zsh"

# Load conf.d if enabled
if [[ "${ENABLE_CONF_D:-1}" == "1" ]] && [[ -d "$ZDOTDIR/conf.d" ]]; then
    for conf in "$ZDOTDIR"/conf.d/[0-9]*.zsh(N); do
        source "$conf"
    done
fi

# Mark successful initialization
# Phase completion and cleanup
if ((PHASE_CORE_INIT)); then
    export ZSH_INIT_LOADED=1
    __set_state "complete" "true"
    __log_info "Core initialization completed successfully"

    # Restore original shell options with selective strict mode
    if [[ "${ENABLE_STRICT_MODE}" == "1" ]]; then
        setopt ${=__ORIGINAL_SHELL_OPTS}
        setopt ERR_EXIT
    else
        setopt ${=__ORIGINAL_SHELL_OPTS}
    fi
else
    __log_error "Initialization incomplete - core phase failed"
    return 1
fi

__log_info "ZSH initialization completed successfully"

# Cleanup
unset __ORIGINAL_SHELL_OPTS

