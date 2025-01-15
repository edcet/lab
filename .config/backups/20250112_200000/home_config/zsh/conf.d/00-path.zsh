#!/bin/zsh

# Core system paths (most specific to least)
typeset -U path
path=(
    /opt/homebrew/bin
    /opt/homebrew/sbin
    /usr/local/bin
    /usr/bin
    /bin
    /usr/local/sbin
    /usr/sbin
    /sbin
    $HOME/.local/bin
    $HOME/bin
    $HOME/.cargo/bin
    $path
)

# Let mise handle language-specific paths
if command -v mise &> /dev/null; then
    eval "$(mise activate zsh)"
fi

# Ensure no duplicates
typeset -U PATH
export PATH
