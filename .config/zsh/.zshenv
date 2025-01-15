# XDG Base Directory Specification
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_STATE_HOME="$HOME/.local/state"

# ZSH specific
export ZDOTDIR="$XDG_CONFIG_HOME/zsh"
export ZSH_CACHE_DIR="$XDG_CACHE_HOME/zsh"

# Ensure directories exist
mkdir -p "$ZSH_CACHE_DIR"

# History
export HISTFILE="$ZDOTDIR/.zsh_history"
export HISTSIZE=10000
export SAVEHIST=10000

# Editor
export EDITOR="code"
export VISUAL="code"

# Development
export MISE_ROOT="$XDG_DATA_HOME/mise"
export MISE_GLOBAL_CONFIG_FILE="$XDG_CONFIG_HOME/mise/config.toml"
export MISE_USE_VERSIONS_HOST=1

# Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"
