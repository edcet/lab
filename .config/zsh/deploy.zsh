#!/usr/bin/env zsh

# Standard XDG Paths - default to standard locations if not set
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"

# Configuration directories
ZSH_CONFIG_DIR="$XDG_CONFIG_HOME/zsh"
ZSH_CACHE_DIR="$XDG_CACHE_HOME/zsh"
ZSH_DATA_DIR="$XDG_DATA_HOME/zsh"
ZSH_STATE_DIR="$XDG_STATE_HOME/zsh"

# Source directories (current locations)
LAB_ZSH_DIR="$HOME/lab/.config/zsh"

# Create timestamp for backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$HOME/zsh_backup_$TIMESTAMP"

# Log file
LOG_FILE="$ZSH_CACHE_DIR/deploy_$TIMESTAMP.log"

# Helper functions
log() {
    echo "$@" | tee -a "$LOG_FILE"
}

backup_file() {
    local src="$1"
    local rel_path="${src#$HOME/}"
    local backup_path="$BACKUP_DIR/$rel_path"
    mkdir -p "$(dirname "$backup_path")"
    [[ -e "$src" ]] && cp -R "$src" "$backup_path"
}

ensure_dir() {
    local dir="$1"
    local mode="${2:-755}"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        chmod "$mode" "$dir"
    fi
}

# Create required directories
log "Creating XDG directory structure..."
ensure_dir "$ZSH_CONFIG_DIR" 700
ensure_dir "$ZSH_CACHE_DIR" 700
ensure_dir "$ZSH_DATA_DIR" 700
ensure_dir "$ZSH_STATE_DIR" 700

# Create subdirectories
ensure_dir "$ZSH_CONFIG_DIR/conf.d" 700
ensure_dir "$ZSH_CONFIG_DIR/functions" 700
ensure_dir "$ZSH_CONFIG_DIR/core" 700
ensure_dir "$ZSH_CONFIG_DIR/plugins" 700
ensure_dir "$ZSH_CONFIG_DIR/completions" 700
ensure_dir "$ZSH_DATA_DIR/history" 700
ensure_dir "$ZSH_CACHE_DIR/patterns" 700

# Backup existing files
log "Creating backups..."
ensure_dir "$BACKUP_DIR"
backup_file "$HOME/.zshenv"
backup_file "$HOME/.zshrc"
backup_file "$HOME/.zprofile"
backup_file "$LAB_ZSH_DIR"
backup_file "$ZSH_CONFIG_DIR"

# Move files to new locations
log "Moving configuration files..."
if [[ -d "$LAB_ZSH_DIR" ]]; then
    # Copy core files
    cp -R "$LAB_ZSH_DIR/core/"* "$ZSH_CONFIG_DIR/core/" 2>/dev/null || true
    
    # Copy conf.d files
    cp -R "$LAB_ZSH_DIR/conf.d/"* "$ZSH_CONFIG_DIR/conf.d/" 2>/dev/null || true
    
    # Copy main config files
    [[ -f "$LAB_ZSH_DIR/.zshenv" ]] && cp "$LAB_ZSH_DIR/.zshenv" "$ZSH_CONFIG_DIR/"
    [[ -f "$LAB_ZSH_DIR/.zshrc" ]] && cp "$LAB_ZSH_DIR/.zshrc" "$ZSH_CONFIG_DIR/"
    
    # Preserve history
    [[ -f "$LAB_ZSH_DIR/.zsh_history" ]] && cp "$LAB_ZSH_DIR/.zsh_history" "$ZSH_DATA_DIR/history/"
fi

# Update symlinks
log "Updating symlinks..."
ln -sf "$ZSH_CONFIG_DIR/.zshenv" "$HOME/.zshenv"

# Create minimal .zshrc if it doesn't exist
if [[ ! -f "$HOME/.zshrc" ]]; then
    echo "source \"$ZSH_CONFIG_DIR/.zshrc\"" > "$HOME/.zshrc"
fi

# Update permissions
log "Setting permissions..."
find "$ZSH_CONFIG_DIR" -type f -exec chmod 600 {} \;
find "$ZSH_CONFIG_DIR" -type d -exec chmod 700 {} \;

# Special handling for AI integration files
log "Setting up AI integration..."
if [[ -d "$ZSH_CONFIG_DIR/conf.d" ]]; then
    for ai_file in "$ZSH_CONFIG_DIR"/conf.d/*ai*.zsh; do
        if [[ -f "$ai_file" ]]; then
            chmod 600 "$ai_file"
        fi
    done
fi

log "Deployment complete. Backup created at $BACKUP_DIR"
log "Log file available at $LOG_FILE"

# Remind user to restart shell
echo "Please restart your shell session to apply changes"

