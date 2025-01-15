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

# Check system requirements
check_requirements() {
    log "Checking system requirements..."

    # Check for curl
    if ! command -v curl &>/dev/null; then
        error "curl is required but not installed. Please install curl first."
    fi

    # Check for git
    if ! command -v git &>/dev/null; then
        error "git is required but not installed. Please install git first."
    fi
}

# Install mise (formerly rtx) - the environment manager
install_mise() {
    log "Installing mise..."
    if ! command -v mise &>/dev/null; then
        curl https://mise.run | sh
        success "mise installed successfully"
    else
        log "mise already installed"
    fi
}

# Setup development environment
setup_environment() {
    log "Setting up development environment..."

    # Install required tools via mise
    mise install

    # Create Python virtual environment
    mise exec python -- python -m venv .venv
    source .venv/bin/activate

    # Install Python dependencies
    mise exec python -- pip install --upgrade pip
    mise exec python -- pip install -e ".[dev]"

    # Install pre-commit hooks
    mise exec python -- pre-commit install --install-hooks

    success "Development environment setup complete"
}

# Setup VS Code
setup_vscode() {
    log "Setting up VS Code..."

    # Install VS Code extensions
    code --install-extension ms-python.python
    code --install-extension ms-python.vscode-pylance
    code --install-extension ms-python.black-formatter
    code --install-extension charliermarsh.ruff
    code --install-extension ms-python.mypy-type-checker
    code --install-extension ms-python.debugpy
    code --install-extension ms-vscode.test-adapter-converter
    code --install-extension ms-vscode.cmake-tools
    code --install-extension eamodio.gitlens
    code --install-extension github.vscode-github-actions
    code --install-extension github.copilot
    code --install-extension github.copilot-chat

    success "VS Code setup complete"
}

# Main setup process
main() {
    log "Starting development environment setup..."

    check_requirements
    install_mise
    setup_environment
    setup_vscode

    success "Setup complete! Your development environment is ready."
    log "To get started, run: source .venv/bin/activate"
}

# Run main function
main
