#!/bin/zsh

# Project Bootstrap System
# Automatically detects and configures newly cloned repositories

# Guard against double-loading
if [[ -n "$__BOOTSTRAP_LOADED" ]]; then
    return 0
fi
__BOOTSTRAP_LOADED=1

# Use system gateway for configuration
sysgate env_set BOOTSTRAP_CONFIG_DIR "${XDG_CONFIG_HOME:-$HOME/.config}/project-bootstrap" permanent
sysgate env_set BOOTSTRAP_CACHE_DIR "${XDG_CACHE_HOME:-$HOME/.cache}/project-bootstrap" permanent
sysgate env_set BOOTSTRAP_DATA_DIR "${XDG_DATA_HOME:-$HOME/.local/share}/project-bootstrap" permanent
sysgate env_set BOOTSTRAP_SECRETS_FILE "$BOOTSTRAP_CONFIG_DIR/secrets.gpg" permanent

# Ensure directories exist through system gateway
sysgate fs_mkdir "$BOOTSTRAP_CONFIG_DIR"
sysgate fs_mkdir "$BOOTSTRAP_CACHE_DIR"
sysgate fs_mkdir "$BOOTSTRAP_DATA_DIR"

# Initialize secrets store if it doesn't exist
if ! sysgate fs_exists "$BOOTSTRAP_SECRETS_FILE"; then
    echo "{}" | gpg --symmetric --output "$BOOTSTRAP_SECRETS_FILE"
fi

# Framework detection patterns
typeset -A __BOOTSTRAP_FRAMEWORKS=(
    [react]="package.json:react"
    [nextjs]="package.json:next"
    [vue]="package.json:vue"
    [django]="requirements.txt:Django"
    [flask]="requirements.txt:Flask"
    [fastapi]="requirements.txt:fastapi"
    [laravel]="composer.json:laravel"
    [spring]="pom.xml:spring-boot"
    [rails]="Gemfile:rails"
)

# Language detection patterns
typeset -A __BOOTSTRAP_LANGUAGES=(
    [python]="requirements.txt|setup.py|pyproject.toml"
    [node]="package.json|yarn.lock|pnpm-lock.yaml"
    [ruby]="Gemfile|.ruby-version"
    [java]="pom.xml|build.gradle"
    [go]="go.mod|go.sum"
    [rust]="Cargo.toml|Cargo.lock"
    [php]="composer.json|composer.lock"
)

# Required variables by framework
typeset -A __BOOTSTRAP_REQUIRED_VARS=(
    [react]="REACT_APP_API_URL REACT_APP_ENV"
    [nextjs]="NEXT_PUBLIC_API_URL NEXT_PUBLIC_ENV"
    [django]="DJANGO_SECRET_KEY DJANGO_DEBUG DJANGO_ALLOWED_HOSTS"
    [flask]="FLASK_APP FLASK_ENV FLASK_SECRET_KEY"
    [fastapi]="API_KEY DATABASE_URL"
    [laravel]="APP_KEY APP_ENV DB_CONNECTION"
)

# Security patterns to check
typeset -A __BOOTSTRAP_SECURITY_PATTERNS=(
    [secrets]="\.env|\.key$|\.pem$|\.crt$"
    [credentials]="password|secret|token|key"
    [sensitive]="\.htpasswd|\.htaccess|\.ssh"
)

# Variable management with encryption
function __bootstrap_get_secret() {
    local key="$1"
    local value

    # Check if GPG is available
    if ! command -v gpg >/dev/null 2>&1; then
        print -P "%F{red}Error: GPG is not installed%f"
        return 1
    fi

    # Decrypt and retrieve value
    value=$(gpg --quiet --decrypt "$BOOTSTRAP_SECRETS_FILE" 2>/dev/null | jq -r ".[\"$key\"] // empty")

    if [[ -z "$value" ]]; then
        # Prompt for value if not found
        print -P "%F{yellow}Secret '$key' not found. Please enter value:%f"
        read -s "value?> "
        echo

        # Store new value
        __bootstrap_set_secret "$key" "$value"
    fi

    echo "$value"
}

function __bootstrap_set_secret() {
    local key="$1"
    local value="$2"
    local temp_file=$(mktemp)

    # Read existing secrets
    if ! gpg --quiet --decrypt "$BOOTSTRAP_SECRETS_FILE" 2>/dev/null > "$temp_file"; then
        echo "{}" > "$temp_file"
    fi

    # Update secret
    jq --arg k "$key" --arg v "$value" '. + {($k): $v}' "$temp_file" | \
        gpg --symmetric --output "$BOOTSTRAP_SECRETS_FILE"

    rm -f "$temp_file"
}

# Project type detection with security checks
function __bootstrap_detect_project() {
    local dir="$1"
    local -a languages frameworks vars
    local debug=${BOOTSTRAP_DEBUG:-0}

    cd "$dir" || return 1

    # Check for security issues
    for key in secrets credentials sensitive; do
        local pattern="$__BOOTSTRAP_SECURITY_PATTERNS[$key]"
        local files=($(find . -type f -regex ".*${pattern}.*" 2>/dev/null))
        if (( ${#files} > 0 )); then
            print -P "%F{red}Warning: Found potentially sensitive $key files:%f"
            printf '%s\n' "${files[@]}"
        fi
    done

    # Detect languages
    for lang pattern in ${(kv)__BOOTSTRAP_LANGUAGES}; do
        if eval "[[ -f *($pattern) ]]"; then
            languages+=($lang)
            [[ $debug -eq 1 ]] && print -P "%F{cyan}Detected language: $lang%f"
        fi
    done

    # Detect frameworks
    for framework pattern in ${(kv)__BOOTSTRAP_FRAMEWORKS}; do
        local file="${pattern%%:*}"
        local marker="${pattern#*:}"
        if [[ -f "$file" ]] && grep -q "$marker" "$file" 2>/dev/null; then
            frameworks+=($framework)
            [[ $debug -eq 1 ]] && print -P "%F{cyan}Detected framework: $framework%f"

            # Check required variables
            if [[ -n "${__BOOTSTRAP_REQUIRED_VARS[$framework]}" ]]; then
                for var in ${=__BOOTSTRAP_REQUIRED_VARS[$framework]}; do
                    vars+=($var)
                done
            fi
        fi
    done

    # Return results
    if (( ${#languages} > 0 || ${#frameworks} > 0 || ${#vars} > 0 )); then
        __bootstrap_setup_project "$dir" "${(j:,:)languages}" "${(j:,:)frameworks}" "$vars"
    else
        print -P "%F{yellow}No supported project structure detected in $dir%f"
    fi
}

# Project setup with environment configuration
function __bootstrap_setup_project() {
    local dir="$1"
    local languages="$2"
    local frameworks="$3"
    local -a vars=("${@:4}")
    local debug=${BOOTSTRAP_DEBUG:-0}

    cd "$dir" || return 1

    # Create virtual environment for Python projects
    if [[ "$languages" == *"python"* ]]; then
        if ! command -v python3 >/dev/null 2>&1; then
            print -P "%F{red}Error: Python 3 is not installed%f"
            return 1
        fi

        python3 -m venv .venv
        source .venv/bin/activate

        # Install dependencies
        if [[ -f "requirements.txt" ]]; then
            pip install -r requirements.txt
        elif [[ -f "setup.py" ]]; then
            pip install -e .
        elif [[ -f "pyproject.toml" ]]; then
            pip install -e .
        fi
    fi

    # Setup Node.js projects
    if [[ "$languages" == *"node"* ]]; then
        if ! command -v node >/dev/null 2>&1; then
            print -P "%F{red}Error: Node.js is not installed%f"
            return 1
        fi

        # Install dependencies based on lock file
        if [[ -f "yarn.lock" ]]; then
            yarn install
        elif [[ -f "pnpm-lock.yaml" ]]; then
            pnpm install
        else
            npm install
        fi
    fi

    # Create environment file
    if [[ ${#vars} -gt 0 ]]; then
        local env_file=".env"
        print -P "%F{blue}Setting up environment variables...%f"

        # Create .env file if it doesn't exist
        touch "$env_file"
        chmod 600 "$env_file"

        # Process each required variable
        for var in $vars; do
            if ! grep -q "^$var=" "$env_file" 2>/dev/null; then
                local value=$(__bootstrap_get_secret "$var")
                echo "$var=$value" >> "$env_file"
            fi
        done
    fi

    # Framework-specific setup
    case "$frameworks" in
        *react*)
            # Setup React development server
            if ! grep -q "\"start\":" package.json 2>/dev/null; then
                jq '.scripts.start = "react-scripts start"' package.json > temp.json && mv temp.json package.json
            fi
            ;;
        *nextjs*)
            # Setup Next.js development server
            if ! grep -q "\"dev\":" package.json 2>/dev/null; then
                jq '.scripts.dev = "next dev"' package.json > temp.json && mv temp.json package.json
            fi
            ;;
        *django*)
            # Setup Django development server
            if [[ ! -f "manage.py" ]]; then
                print -P "%F{red}Error: Django project is missing manage.py%f"
                return 1
            fi
            python manage.py migrate
            ;;
        *flask*|*fastapi*)
            # Setup Python API development server
            if [[ ! -f "app.py" && ! -f "main.py" ]]; then
                print -P "%F{red}Error: Missing main application file%f"
                return 1
            fi
            ;;
    esac

    # Save project state
    __bootstrap_save_state "$dir"

    print -P "%F{green}Project setup complete%f"
}

# Project state management
function __bootstrap_save_state() {
    local dir="$1"
    local state_file="$BOOTSTRAP_DATA_DIR/projects.json"
    local temp_file=$(mktemp)

    # Read existing state
    if [[ -f "$state_file" ]]; then
        cp "$state_file" "$temp_file"
    else
        echo "{}" > "$temp_file"
    fi

    # Update state
    jq --arg dir "$dir" --arg ts "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
       '. + {($dir): {"last_updated": $ts}}' "$temp_file" > "$state_file"

    rm -f "$temp_file"
}

# Project cleanup with age consideration
function __bootstrap_cleanup() {
    local dir="$1"
    local max_age="${2:-30}"  # Default to 30 days
    local force="${3:-0}"
    local debug=${BOOTSTRAP_DEBUG:-0}

    cd "$dir" || return 1

    # Find old virtual environments
    find . -type d -name ".venv" -mtime +"$max_age" -print0 | while IFS= read -r -d '' venv; do
        if [[ $force -eq 1 ]]; then
            rm -rf "$venv"
            [[ $debug -eq 1 ]] && print -P "%F{cyan}Removed old virtual environment: $venv%f"
        else
            print -P "%F{yellow}Would remove old virtual environment: $venv%f"
        fi
    done

    # Find old node_modules
    find . -type d -name "node_modules" -mtime +"$max_age" -print0 | while IFS= read -r -d '' modules; do
        if [[ $force -eq 1 ]]; then
            rm -rf "$modules"
            [[ $debug -eq 1 ]] && print -P "%F{cyan}Removed old node_modules: $modules%f"
        else
            print -P "%F{yellow}Would remove old node_modules: $modules%f"
        fi
    done

    # Find old cache directories
    find . -type d -name ".cache" -o -name "__pycache__" -mtime +"$max_age" -print0 | while IFS= read -r -d '' cache; do
        if [[ $force -eq 1 ]]; then
            rm -rf "$cache"
            [[ $debug -eq 1 ]] && print -P "%F{cyan}Removed old cache: $cache%f"
        else
            print -P "%F{yellow}Would remove old cache: $cache%f"
        fi
    done
}

# Initialize on load
__bootstrap_init() {
    # Create required directories through system gateway
    sysgate fs_mkdir "$BOOTSTRAP_CONFIG_DIR"
    sysgate fs_mkdir "$BOOTSTRAP_CACHE_DIR"
    sysgate fs_mkdir "$BOOTSTRAP_DATA_DIR"

    # Initialize secrets store if needed
    if ! sysgate fs_exists "$BOOTSTRAP_SECRETS_FILE"; then
        echo "{}" | gpg --symmetric --output "$BOOTSTRAP_SECRETS_FILE"
    fi

    print -P "%F{green}Project bootstrap system initialized%f"
}

# Export public interface
export -f __bootstrap_detect_project
export -f __bootstrap_cleanup
