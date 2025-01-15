#!/usr/bin/env zsh

# Git Autobuilder Configuration Loader
# AI-powered git workflow with progressive learning

# Feature discovery system
typeset -gA __git_expertise_levels=(
    'beginner'    'Basic git operations with AI assistance'
    'regular'     'Common workflows and automation'
    'advanced'    'Complex operations and custom hooks'
    'expert'      'Advanced automation and CI/CD integration'
)

typeset -gA __git_feature_categories=(
    'essential'   'Core git operations'
    'protective'  'Security and validation'
    'productive'  'Workflow automation'
    'supportive'  'Helper functions'
    'preferential' 'Custom configurations'
)

# Source core module
source "${ZDOTDIR}/core/git_autobuilder.zsh"

# Enhanced git commands with progressive discovery
function githelp() {
    local topic="${1:-overview}"
    local detail="${2:-basic}"

    case "$topic" in
        overview)
            print -P "%F{blue}Git Autobuilder Help%f"
            print -P "%F{cyan}Available Commands:%f"
            print -P "  gac     - Auto-commit with AI message"
            print -P "  gap     - Auto-push with security checks"
            print -P "  gapr    - Create PR with AI title"
            print -P "  gwi     - Initialize workspace"
            print -P "  gws     - Scan workspace"
            print -P "  gwm     - Monitor workspace"
            ;;
        features)
            print -P "%F{blue}Feature Categories:%f"
            for category desc in ${(kv)__git_feature_categories}; do
                print -P "%F{yellow}$category:%f $desc"
            done
            ;;
        expertise)
            print -P "%F{blue}Expertise Levels:%f"
            for level desc in ${(kv)__git_expertise_levels}; do
                print -P "%F{yellow}$level:%f $desc"
            done
            ;;
        security)
            print -P "%F{blue}Security Features:%f"
            print -P "- Pre-commit hooks for sensitive data detection"
            print -P "- Automated security scanning"
            print -P "- GPG signing integration"
            ;;
        ai)
            print -P "%F{blue}AI Features:%f"
            print -P "- Smart commit message generation"
            print -P "- Intelligent PR title suggestions"
            print -P "- Code review assistance"
            ;;
        *)
            print -P "%F{red}Unknown topic: $topic%f"
            print -P "Try: overview, features, expertise, security, ai"
            ;;
    esac
}

# Enhanced git status with context
function gitstatus() {
    local detail="${1:-basic}"

    print -P "%F{blue}Git Workspace Status:%f"
    case "$detail" in
        basic)
            git status -s
            ;;
        detailed)
            print -P "%F{yellow}Branch Information:%f"
            git branch -vv
            print -P "\n%F{yellow}Changes:%f"
            git status
            print -P "\n%F{yellow}Recent Commits:%f"
            git log --oneline -n 5
            ;;
        security)
            print -P "%F{yellow}Security Status:%f"
            if command -v gitleaks >/dev/null 2>&1; then
                gitleaks detect --no-git || echo "Security issues detected!"
            else
                print -P "%F{red}gitleaks not installed%f"
            fi
            ;;
        *)
            print -P "%F{red}Unknown detail level: $detail%f"
            print -P "Try: basic, detailed, security"
            ;;
    esac
}

# Enhanced git commands
alias gac='__auto_commit'  # Auto-commit with AI message
alias gap='__auto_push'    # Auto-push with security checks
alias gapr='__auto_pr'     # Create PR with AI title
alias gwi='__init_workspace'  # Initialize workspace
alias gws='__scan_workspace'  # Scan workspace
alias gwm='__monitor_workspace'  # Monitor workspace

# Git completions
if [[ -f /usr/share/zsh/functions/Completion/Unix/_git ]]; then
    zstyle ':completion:*:*:git:*' script /usr/share/zsh/functions/Completion/Unix/_git
    fpath=(/usr/share/zsh/functions/Completion/Unix $fpath)
fi

# Custom completions for autobuilder commands
function _git_autobuilder_commands() {
    local -a commands
    commands=(
        'gac:Auto-commit with AI message'
        'gap:Auto-push with security checks'
        'gapr:Create PR with AI title'
        'gwi:Initialize workspace'
        'gws:Scan workspace'
        'gwm:Monitor workspace'
    )
    _describe 'command' commands
}

compdef _git_autobuilder_commands gac gap gapr gwi gws gwm

# Git hooks setup
function __setup_git_hooks() {
    if [[ ! -d .git/hooks ]]; then
        return
    fi

    # Pre-commit hook for AI review
    cat > .git/hooks/pre-commit << 'EOL'
#!/bin/sh
if command -v gitleaks >/dev/null 2>&1; then
    if ! gitleaks detect --no-git; then
        echo "Security scan failed. Please check for sensitive data."
        exit 1
    fi
fi

# Run auto-commit if available
if command -v __auto_commit >/dev/null 2>&1; then
    message=$(git log -1 --pretty=%B)
    if [[ -z "$message" ]]; then
        message=$(__generate_commit_message)
    fi
    git commit -m "$message"
fi
exit 0
EOL
    chmod +x .git/hooks/pre-commit

    # Pre-push hook for security scan
    cat > .git/hooks/pre-push << 'EOL'
#!/bin/sh
if command -v gitleaks >/dev/null 2>&1; then
    if ! gitleaks detect --no-git; then
        echo "Security scan failed. Please check for sensitive data."
        exit 1
    fi
fi
exit 0
EOL
    chmod +x .git/hooks/pre-push
}

# Environment setup
if [[ -f "${XDG_CONFIG_HOME}/git-autobuilder/config.toml" ]]; then
    # Load GitHub token if available
    if [[ -n "${GITHUB_TOKEN}" ]]; then
        export GH_TOKEN="${GITHUB_TOKEN}"  # For GitHub CLI
    fi

    # Configure git
    git config --global commit.gpgsign true 2>/dev/null || true
    git config --global pull.rebase true 2>/dev/null || true
    git config --global push.autoSetupRemote true 2>/dev/null || true
fi

# Initialize hooks if in a git repository
if git rev-parse --git-dir >/dev/null 2>&1; then
    __setup_git_hooks
fi

# Initialize with user guidance
print -P "%F{green}Git Autobuilder: Enhanced git commands loaded%f"
print -P "%F{blue}Type 'githelp' for available commands and features%f"
