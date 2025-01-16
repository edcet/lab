    [sync_count]=0
    [errors]=0
    [status]="initialized"
)
EOL
    fi

    # Source state file
    if [[ -f "$SYNC_STATE_FILE" ]]; then
        source "$SYNC_STATE_FILE"
    else
        print -P "%F{red}Error: Failed to initialize state file%f"
        return 1
    fi
}

# Initialize state on load
__sync_init_state || return 1

# Export public interface
export -f __sync_orchestrate
