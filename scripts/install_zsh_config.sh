#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper functions
log() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Ensure XDG directories exist
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"

# Create Zsh directories
ZDOTDIR="${XDG_CONFIG_HOME}/zsh"
mkdir -p "${ZDOTDIR}/core"
mkdir -p "${ZDOTDIR}/conf.d"

# Copy configuration files
log "Installing Zsh configuration files..."

# Core modules
cp .config/zsh/core/*.zsh "${ZDOTDIR}/core/"
chmod 644 "${ZDOTDIR}"/core/*.zsh

# Configuration files
cp .config/zsh/conf.d/*.zsh "${ZDOTDIR}/conf.d/"
chmod 644 "${ZDOTDIR}"/conf.d/*.zsh

# Main config files
cp .config/zsh/.zshrc "${ZDOTDIR}/"
cp .config/zsh/.zshenv "${ZDOTDIR}/"
chmod 644 "${ZDOTDIR}"/.zsh*

# Create necessary directories for git autobuilder
mkdir -p "${XDG_CONFIG_HOME}/git-autobuilder"
mkdir -p "${XDG_DATA_HOME}/git-autobuilder/logs"
mkdir -p "${XDG_CACHE_HOME}/git-autobuilder"

# Set up default git autobuilder config if it doesn't exist
if [[ ! -f "${XDG_CONFIG_HOME}/git-autobuilder/config.toml" ]]; then
    cat > "${XDG_CONFIG_HOME}/git-autobuilder/config.toml" << 'EOL'
[github]
username = ""
token = ""
default_repo = ""

[commit]
types = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "test",
    "chore"
]
scopes = [
    "core",
    "ui",
    "docs",
    "tests",
    "config"
]

[ai]
enhance_commits = true
suggest_branches = true
review_code = true
resolve_conflicts = true

[security]
sign_webhooks = true
verify_commits = true
scan_secrets = true
EOL
fi

# Update shell environment
if [[ -f "$HOME/.zshenv" ]]; then
    if ! grep -q "ZDOTDIR=" "$HOME/.zshenv"; then
        echo "export ZDOTDIR=\"\${XDG_CONFIG_HOME:-\$HOME/.config}/zsh\"" >> "$HOME/.zshenv"
    fi
else
    echo "export ZDOTDIR=\"\${XDG_CONFIG_HOME:-\$HOME/.config}/zsh\"" > "$HOME/.zshenv"
fi

success "Zsh configuration installed successfully"
log "Please restart your shell or run 'source \$HOME/.zshenv' to apply changes"
