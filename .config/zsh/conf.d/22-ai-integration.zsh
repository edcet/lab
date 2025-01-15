#!/usr/bin/env zsh

# AI Integration System
# Connects autonomous agent with development environment

# Error handling
function __ai_handle_error() {
    local code=$1
    local message=$2
    local context=$3

    __envmgr_log "ERROR" "[AI:${context}] ${message} (code: ${code})"
    return ${code}
}

# Ensure required components
function __ensure_ai_components() {
    typeset -f __envmgr_log >/dev/null || {
        echo "Error: Environment manager not loaded"
        return 1
    }

    typeset -f __auto_commit >/dev/null || {
        echo "Error: Git autobuilder not loaded"
        return 2
    }

    [[ -f "${ZDOTDIR}/core/git_autobuilder.zsh" ]] || {
        echo "Error: Git autobuilder core not found"
        return 3
    }

    return 0
}

# AI-enhanced project initialization
function ai_init_project() {
    local name="$1"
    local type="${2:-python}"
    local path="${3:-./$name}"

    __ensure_ai_components || return $?

    # Initialize project with standard tooling
    init_project "$name" "$type" "$path" || {
        __ai_handle_error 4 "Failed to initialize project" "init"
        return 4
    }

    # Set up AI configuration
    cat > "$path/.aiconfig.toml" << EOL || return 5
[ai]
pattern_recognition = true
learning_enabled = true
performance_tracking = true
evolution_enabled = true

[memory]
store_patterns = true
learn_from_history = true
optimize_retrieval = true
max_memory_items = 10000

[evolution]
performance_threshold = 0.85
efficiency_minimum = 0.75
cost_optimization = true
evolution_rate = "progressive"

[performance]
track_metrics = true
metrics_history_size = 1000
efficiency_weight = 0.4
cost_weight = 0.3
success_weight = 0.3
EOL

    # Initialize git attributes for AI
    cat > "$path/.gitattributes" << EOL || return 6
*.py diff=python
*.js diff=javascript
*.html diff=html
*.css diff=css
*.md diff=markdown
EOL

    # Set up pre-commit hooks for AI analysis
    mkdir -p "$path/.git/hooks"
    cat > "$path/.git/hooks/pre-commit" << 'EOL' || return 7
#!/bin/sh
# AI-enhanced pre-commit hook

# Run pattern analysis
if command -v python3 >/dev/null 2>&1; then
    if [[ -f "src/core/ai/pattern_recognition.py" ]]; then
        python3 src/core/ai/pattern_recognition.py --analyze-staged
    fi
fi

# Run security checks
if command -v gitleaks >/dev/null 2>&1; then
    if ! gitleaks detect --no-git; then
        echo "Security check failed. Please review changes."
        exit 1
    fi
fi

exit 0
EOL
    chmod +x "$path/.git/hooks/pre-commit"

    __envmgr_log "INFO" "AI configuration initialized for $path"
    return 0
}

# AI-enhanced feature management
function ai_feature() {
    local action="$1"
    shift

    __ensure_ai_components || return $?

    case "$action" in
        start)
            local name="$1"
            local base="${2:-main}"

            # Start feature with isolated environment
            start_feature "$name" "$base" || return $?

            # Initialize feature-specific AI tracking
            mkdir -p ".ai/features/$name"
            cat > ".ai/features/$name/metadata.toml" << EOL || return 8
[feature]
name = "$name"
started = "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
base_branch = "$base"

[metrics]
changes_analyzed = 0
patterns_recognized = 0
performance_score = 0.0
EOL
            ;;

        complete)
            local name="$1"
            local target="${2:-main}"

            # Analyze feature impact
            if [[ -d ".ai/features/$name" ]]; then
                python3 -c '
import sys, toml
from datetime import datetime
from pathlib import Path

feature_dir = Path(".ai/features") / sys.argv[1]
metadata_file = feature_dir / "metadata.toml"

if metadata_file.exists():
    data = toml.load(metadata_file)
    data["completion"] = {
        "date": datetime.utcnow().isoformat(),
        "changes": len(list(Path().glob("**/*"))),
        "impact_score": 0.8  # TODO: Calculate real impact
    }
    with open(metadata_file, "w") as f:
        toml.dump(data, f)
' "$name" || true
            fi

            # Complete feature normally
            complete_feature "$name" "$target"
            ;;

        analyze)
            local name="$1"
            if [[ ! -d ".ai/features/$name" ]]; then
                __ai_handle_error 9 "Feature not found" "analyze"
                return 9
            fi

            # Run pattern analysis
            python3 src/core/ai/pattern_recognition.py --analyze-feature "$name" || true

            # Show metrics
            if [[ -f ".ai/features/$name/metadata.toml" ]]; then
                print -P "%F{blue}Feature Analysis: $name%f"
                python3 -c '
import sys, toml
from pathlib import Path

metadata_file = Path(".ai/features") / sys.argv[1] / "metadata.toml"
if metadata_file.exists():
    data = toml.load(metadata_file)
    print(f"Started: {data.get('feature', {}).get('started', 'unknown')}")
    print(f"Changes Analyzed: {data.get('metrics', {}).get('changes_analyzed', 0)}")
    print(f"Patterns Recognized: {data.get('metrics', {}).get('patterns_recognized', 0)}")
    print(f"Performance Score: {data.get('metrics', {}).get('performance_score', 0.0):.2f}")
    if "completion" in data:
        print(f"Completed: {data['completion']['date']}")
        print(f"Impact Score: {data['completion']['impact_score']:.2f}")
' "$name"
            fi
            ;;

        *)
            print -P "%F{red}Unknown action: $action%f"
            print -P "Try: start, complete, analyze"
            return 1
            ;;
    esac
}

# AI-enhanced project analysis
function ai_analyze() {
    local path="${1:-.}"

    __ensure_ai_components || return $?

    print -P "%F{blue}AI Project Analysis%f"

    # Run pattern recognition
    if [[ -f "src/core/ai/pattern_recognition.py" ]]; then
        print -P "\n%F{yellow}Pattern Analysis:%f"
        python3 src/core/ai/pattern_recognition.py --analyze-project "$path" || true
    fi

    # Run learning engine analysis
    if [[ -f "src/core/ai/learning_engine.py" ]]; then
        print -P "\n%F{yellow}Learning Analysis:%f"
        python3 src/core/ai/learning_engine.py --analyze-project "$path" || true
    fi

    # Show project metrics
    if [[ -f ".aiconfig.toml" ]]; then
        print -P "\n%F{yellow}Project Metrics:%f"
        python3 -c '
import toml
from pathlib import Path

config_file = Path(".aiconfig.toml")
if config_file.exists():
    data = toml.load(config_file)
    print(f"Pattern Recognition: {data.get('ai', {}).get('pattern_recognition', False)}")
    print(f"Learning Enabled: {data.get('ai', {}).get('learning_enabled', False)}")
    print(f"Evolution Enabled: {data.get('ai', {}).get('evolution_enabled', False)}")
'
    fi

    return 0
}

# Register commands
alias ainit='ai_init_project'
alias aifeat='ai_feature'
alias aianalyze='ai_analyze'

# Command completion
function _ai_commands() {
    local -a commands
    commands=(
        'ainit:Initialize AI-enhanced project'
        'aifeat:Manage AI-enhanced features'
        'aianalyze:Run AI project analysis'
    )
    _describe 'command' commands
}

compdef _ai_commands ainit aifeat aianalyze

# Help function
function ai_help() {
    print -P "%F{blue}AI Integration Commands:%f"
    print -P "  ainit     - Initialize AI-enhanced project"
    print -P "  aifeat    - Manage AI-enhanced features"
    print -P "  aianalyze - Run AI project analysis"
}

# Initialize
__envmgr_log "INFO" "AI integration system loaded"
print -P "%F{green}AI integration commands loaded%f"
print -P "%F{blue}Type 'ai_help' for available commands%f"
