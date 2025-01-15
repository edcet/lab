#!/usr/bin/env zsh

# Bulletproof path resolution
__resolve_root() {
    local candidate

    # Try to find project root from script location
    if [[ -n $0 && $0 != "zsh" ]]; then
        candidate=${0:A:h:h:h:h}
        [[ -d $candidate/src/core/shell ]] && echo $candidate && return 0
    }

    # Try current directory
    candidate=$PWD
    while [[ $candidate != "/" ]]; do
        [[ -d $candidate/src/core/shell ]] && echo $candidate && return 0
        candidate=${candidate:h}
    done

    # Try relative to ZDOTDIR
    candidate=${ZDOTDIR:-$HOME}
    [[ -d $candidate/src/core/shell ]] && echo $candidate && return 0

    return 1
}

# Resolve critical paths
INTELLIGENT_SHELL_ROOT=$(__resolve_root) || {
    print -P "%F{red}Fatal: Could not resolve project root%f"
    return 1
}

INTELLIGENT_SHELL_MODULE=$INTELLIGENT_SHELL_ROOT/src/core/shell/intelligent_shell.zsh
INTELLIGENT_SHELL_STATE=${XDG_STATE_HOME:-$HOME/.local/state}/zsh

# Verify module exists
[[ -f $INTELLIGENT_SHELL_MODULE ]] || {
    print -P "%F{red}Fatal: Intelligent shell module not found at $INTELLIGENT_SHELL_MODULE%f"
    return 1
}

# Verify module is readable
[[ -r $INTELLIGENT_SHELL_MODULE ]] || {
    print -P "%F{red}Fatal: Cannot read intelligent shell module%f"
    return 1
}

# Ensure state directory structure
for dir in logs metrics history patterns; do
    mkdir -p $INTELLIGENT_SHELL_STATE/$dir || {
        print -P "%F{red}Fatal: Could not create $dir directory%f"
        return 1
    }
    [[ -w $INTELLIGENT_SHELL_STATE/$dir ]] || {
        print -P "%F{red}Fatal: Cannot write to $dir directory%f"
        return 1
    }
done

# Load core module
source $INTELLIGENT_SHELL_MODULE || {
    print -P "%F{red}Fatal: Failed to source intelligent shell module%f"
    return 1
}

# Verify core functions loaded
for func in _init_intelligent_shell __update_context; do
    (( ${+functions[$func]} )) || {
        print -P "%F{red}Fatal: Core function $func not loaded%f"
        return 1
    }
done

# Set up configuration
zstyle ':intelligent-shell:learning' threshold '5'
zstyle ':intelligent-shell:history' size '100'
zstyle ':intelligent-shell:state' dir $INTELLIGENT_SHELL_STATE
zstyle ':intelligent-shell:logging' enabled 'true'
zstyle ':intelligent-shell:metrics' enabled 'true'

# Initialize system
_init_intelligent_shell || {
    print -P "%F{red}Fatal: Initialization failed%f"
    return 1
}

# Load hook system
autoload -Uz add-zsh-hook || {
    print -P "%F{red}Fatal: Could not load hook system%f"
    return 1
}

# Register hooks
add-zsh-hook chpwd __update_context || {
    print -P "%F{red}Fatal: Could not register context hook%f"
    return 1
}

print -P "%F{green}Intelligent shell initialized successfully%f"
return 0
