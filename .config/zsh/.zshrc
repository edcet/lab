# ZSH Options
setopt AUTO_CD              # cd by typing directory name
setopt EXTENDED_HISTORY     # record timestamp of command
setopt SHARE_HISTORY       # share history between all sessions
setopt HIST_EXPIRE_DUPS_FIRST # delete duplicates first when HISTFILE size exceeds HISTSIZE
setopt HIST_IGNORE_DUPS    # ignore duplicated commands history list
setopt HIST_IGNORE_SPACE   # ignore commands that start with space
setopt HIST_VERIFY        # show command with history expansion before running it
setopt CORRECT            # auto correct mistakes
setopt COMPLETE_IN_WORD   # complete from both ends of a word

# Initialize completion system
autoload -Uz compinit
compinit -d "$ZSH_CACHE_DIR/zcompdump-$ZSH_VERSION"

# Initialize environment management first
if command -v mise &> /dev/null; then
    eval "$(mise activate zsh)"
fi

# Load core configuration
for conf in "$ZDOTDIR/conf.d/"*.zsh(N); do
    source "$conf"
done

# Initialize interactive tools last
if command -v starship &> /dev/null; then
    eval "$(starship init zsh)"
fi

if command -v zoxide &> /dev/null; then
    eval "$(zoxide init zsh)"
fi

# Display environment info if requested
if [[ -n "$SHOW_ENV_ON_LOAD" ]]; then
    paths  # Show path priorities
    mise ls  # Show active tools
fi
