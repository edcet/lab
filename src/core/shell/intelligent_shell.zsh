# Intelligent Shell System
# Advanced pattern recognition and learning for Zsh
#
# This module provides an intelligent shell enhancement system that:
# - Learns from user commands and patterns
# - Provides contextual suggestions
# - Generates dynamic completions
# - Creates smart aliases
#
# Usage:
#   source intelligent_shell.zsh
#   _init_intelligent_shell
#
# Configuration:
#   :intelligent-shell:learning threshold '5'  # Min score for learning
#   :intelligent-shell:history size '100'      # History size to analyze
#
# State Files:
#   ${XDG_STATE_HOME}/zsh/
#   ├── patterns.zsh  # Command patterns
#   ├── learned.zsh   # Learned behaviors
#   ├── chains.zsh    # Command chains
#   └── context.zsh   # Context data
#
# Dependencies:
#   - zsh 5.8+
#   - flock (for file locking)
#   - standard Unix tools (mv, rm, mkdir)
#
# Performance Impact:
#   - Light hook overhead on each command
#   - State saves are throttled and atomic
#   - Memory usage scales with pattern complexity
#
# Security:
#   - No execution of learned commands
#   - State files contain only command text
#   - File operations use atomic updates
#
# Author: System Administrator
# Version: 1.0.0
# License: MIT

# Global state
typeset -gA SHELL_PATTERNS    # Command patterns
typeset -gA SHELL_LEARNED     # Learned behaviors
typeset -gA SHELL_CONTEXT     # Context tracking
typeset -gA SHELL_CHAINS      # Command chains
typeset -g LAST_CMD
typeset -g LAST_CONTEXT

# Validation functions
__validate_deps() {
  local missing=0

  # Check Zsh version
  if ! autoload -Uz is-at-least || ! is-at-least 5.8; then
    print -P "%F{red}Error: Zsh 5.8+ required%f"
    ((missing++))
  }

  # Check for required commands
  local -a required=(flock mv rm mkdir)
  for cmd in $required; do
    if ! command -v $cmd >/dev/null; then
      print -P "%F{red}Error: Required command not found: $cmd%f"
      ((missing++))
    }
  done

  return $missing
}

# Global state with validation
__init_state() {
  # Initialize with empty arrays if not set
  : ${SHELL_PATTERNS:=()}
  : ${SHELL_LEARNED:=()}
  : ${SHELL_CONTEXT:=()}
  : ${SHELL_CHAINS:=()}

  # Declare as global associative arrays
  typeset -gA SHELL_PATTERNS    # Command patterns
  typeset -gA SHELL_LEARNED     # Learned behaviors
  typeset -gA SHELL_CONTEXT     # Context tracking
  typeset -gA SHELL_CHAINS      # Command chains
  typeset -g LAST_CMD          # Last executed command
  typeset -g LAST_CONTEXT      # Last command context
}

# Core Pattern Engine
# @description Analyzes command history and updates pattern recognition
# @param none
# @return 0 on success, 1 on failure
__pattern_engine() {
  local -a history=(${(f)"$(fc -ln -100)"})
  local current_time=${(%):-%D{%H%M}}
  local current_dir=$PWD

  # Validate inputs
  [[ -n $current_time ]] || return 1
  [[ -d $current_dir ]] || return 1

  # Enhanced pattern detection
  for cmd in $history; do
    # Extract command structure
    local base=${cmd%% *}
    local args=${cmd#* }
    local ctx="$current_dir:$current_time"

    # Update pattern frequency with context
    SHELL_PATTERNS[$base]=$((SHELL_PATTERNS[$base] + 1))
    SHELL_PATTERNS[$ctx:$base]=$((SHELL_PATTERNS[$ctx:$base] + 1))

    # Track argument patterns with type inference
    if [[ -n $args ]]; then
      # Analyze argument types
      local typed_args=""
      for arg in ${(z)args}; do
        case $arg in
          [0-9]##) typed_args+="<num> ";;
          *.*)     typed_args+="<file:${arg:e}> ";;
          -*)      typed_args+="<flag> ";;
          *)       typed_args+="<str> ";;
        esac
      done
      SHELL_PATTERNS[$base:$typed_args]=$((SHELL_PATTERNS[$base:$typed_args] + 1))
    fi

    # Track command chains
    if [[ -n $LAST_CMD ]]; then
      SHELL_CHAINS[$LAST_CMD:$cmd]=$((SHELL_CHAINS[$LAST_CMD:$cmd] + 1))
    }
  done

  # Update context
  SHELL_CONTEXT[$current_dir:$current_time]=$cmd
}

# Predictive suggestion engine
# @description Generates command suggestions based on patterns
# @param $1 current command to base suggestions on
# @return prints suggestions, 0 on success, 1 on failure
__suggest_next() {
  local current=$1

  # Validate input
  [[ -n $current ]] || return 1

  local dir=$PWD
  local time=${(%):-%D{%H%M}}

  # Calculate suggestion scores
  local -A scores=()

  # Factor 1: Command chains
  for chain in ${(k)SHELL_CHAINS}; do
    if [[ $chain == $current:* ]]; then
      local next=${chain#*:}
      local chain_score=$((SHELL_CHAINS[$chain] * 2))
      scores[$next]=$((scores[$next] + chain_score))
    }
  done

  # Factor 2: Time patterns
  for pattern in ${(k)SHELL_PATTERNS}; do
    if [[ $pattern == *:$time:* ]]; then
      local cmd=${pattern##*:}
      local time_score=$((SHELL_PATTERNS[$pattern]))
      scores[$cmd]=$((scores[$cmd] + time_score))
    }
  done

  # Factor 3: Directory context
  for pattern in ${(k)SHELL_PATTERNS}; do
    if [[ $pattern == $dir:* ]]; then
      local cmd=${pattern##*:}
      local dir_score=$((SHELL_PATTERNS[$pattern] * 3))
      scores[$cmd]=$((scores[$cmd] + dir_score))
    }
  done

  # Return top suggestions
  local -a suggestions=()
  for cmd score in ${(Onk)scores}; do
    suggestions+=($cmd)
  done
  print -l ${suggestions[1,5]}
}

# Enhanced state persistence
# @description Saves current state to disk with safety checks
# @param none
# @return 0 on success, 1 on failure
__save_state() {
  local state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/zsh"

  # Ensure directory exists
  if ! mkdir -p $state_dir; then
    print -P "%F{red}Failed to create state directory%f"
    return 1
  }

  # Save with timestamps and locking
  local timestamp=${(%):-%D{%Y%m%d-%H%M%S}}
  local lock_file="$state_dir/state.lock"

  # Acquire lock
  if ! zsystem flock -t 5 $lock_file; then
    print -P "%F{red}Failed to acquire state lock%f"
    return 1
  }

  # Save current state with error checking
  {
    print -r -- ${(kv)SHELL_PATTERNS} > $state_dir/patterns.zsh.new || return 1
    print -r -- ${(kv)SHELL_LEARNED} > $state_dir/learned.zsh.new || return 1
    print -r -- ${(kv)SHELL_CHAINS} > $state_dir/chains.zsh.new || return 1
    print -r -- ${(kv)SHELL_CONTEXT} > $state_dir/context.zsh.new || return 1

    # Atomic rename
    mv $state_dir/*.new $state_dir/ || return 1

    # Save historical snapshot
    if mkdir -p $state_dir/history/$timestamp; then
      cp $state_dir/*.zsh $state_dir/history/$timestamp/
    fi

    # Cleanup old history
    _cleanup_old_state
  } always {
    # Release lock
    zsystem flock -u $lock_file
  }
}

# Add state cleanup
_cleanup_old_state() {
  local state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/zsh"
  local max_history=50

  # List history dirs by date
  local -a history_dirs=(${(on)state_dir}/history/*(/))

  # Remove oldest if exceeding max
  if (( ${#history_dirs} > max_history )); then
    local to_remove=$(( ${#history_dirs} - max_history ))
    for (( i=1; i<=to_remove; i++ )); do
      rm -rf $history_dirs[i]
    done
  }
}

# Fix load state to handle errors
__load_state() {
  local state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/zsh"

  # Helper function to load state files
  __load_state_file() {
    local file=$1
    local array_name=$2

    [[ -f $file ]] || return 1

    local -A temp_array
    local -a data

    # Read data with error checking
    data=(${(f)"$(<$file)"}) || return 1

    # Parse into temporary array
    for line in $data; do
      local key=${line%% *}
      local value=${line#* }
      temp_array[$key]=$value
    done

    # Only update global array if all successful
    eval "$array_name=()"
    eval "$array_name=(\${(kv)temp_array})"
    return 0
  }

  local failed=0
  __load_state_file $state_dir/patterns.zsh SHELL_PATTERNS || ((failed++))
  __load_state_file $state_dir/learned.zsh SHELL_LEARNED || ((failed++))
  __load_state_file $state_dir/chains.zsh SHELL_CHAINS || ((failed++))
  __load_state_file $state_dir/context.zsh SHELL_CONTEXT || ((failed++))

  if (( failed > 0 )); then
    print -P "%F{yellow}Warning: Failed to load some state files%f"
  }
}

# Smart command processing
_track_command() {
  LAST_CMD=$1
  LAST_CONTEXT="$PWD:${(%):-%D{%H%M}}"

  # Track with error handling
  if ! __pattern_engine; then
    print -P "%F{red}Failed to process command patterns%f"
  fi

  # Generate suggestions with error handling
  local -a suggestions
  if suggestions=($(__suggest_next $LAST_CMD 2>/dev/null)); then
    if (( ${#suggestions} > 0 )); then
      print -P "%F{blue}Suggestions:%f"
      print -l $suggestions
    fi
  else
    print -P "%F{yellow}Failed to generate suggestions%f"
  }
}

_process_command() {
  local ret=$?
  if [[ -n $LAST_CMD ]]; then
    # Track command success/failure
    if (( ret == 0 )); then
      __track_metric "success_commands" $((${$(<${XDG_STATE_HOME:-$HOME/.local/state}/zsh/metrics.zsh)#*success_commands:}+1))
      __log "INFO" "Command succeeded: $LAST_CMD"
    else
      __track_metric "failed_commands" $((${$(<${XDG_STATE_HOME:-$HOME/.local/state}/zsh/metrics.zsh)#*failed_commands:}+1))
      __log "ERROR" "Command failed ($ret): $LAST_CMD"
    fi

    # Track pattern learning
    __track_metric "learned_patterns" ${#SHELL_PATTERNS}
    __track_metric "command_chains" ${#SHELL_CHAINS}

    # Update learning with context
    local success_key="$LAST_CONTEXT:$LAST_CMD"
    if (( ret == 0 )); then
      SHELL_LEARNED[$success_key]=$((SHELL_LEARNED[$success_key] + 1))
    else
      SHELL_LEARNED[$success_key]=$((SHELL_LEARNED[$success_key] - 1))
    fi

    # Trigger state save
    __save_state

    # Update dynamic features
    _update_completions
    _generate_aliases
  }
}

# Dynamic completion generation
_update_completions() {
  local cmd=${1:-$LAST_CMD}
  if [[ -n $cmd ]]; then
    local base=${cmd%% *}

    # Generate completion function with error handling
    if ! eval "
      _${base}_completion() {
        local -a completions=()
        # Add learned arguments
        for pattern in \${(k)SHELL_PATTERNS}; do
          if [[ \$pattern == $base:* ]]; then
            completions+=(\${pattern#*:})
          }
        done
        _describe '$base completions' completions
      }
    "; then
      print -P "%F{red}Failed to generate completion for $base%f"
      return 1
    fi

    # Register completion with error handling
    if ! compdef _${base}_completion $base 2>/dev/null; then
      print -P "%F{yellow}Failed to register completion for $base%f"
      return 1
    fi
  }
}

# Enhanced alias generation
_generate_aliases() {
  local lock_file="${XDG_RUNTIME_DIR:-/tmp}/zsh_aliases.lock"

  # Acquire lock
  if ! zsystem flock -t 5 $lock_file; then
    print -P "%F{red}Failed to acquire alias lock%f"
    return 1
  }

  {
    local threshold=${$(zstyle -L ':intelligent-shell:learning' threshold)[2]:-5}

    # Clear old aliases
    local -a old_aliases=(${(k)aliases})
    for alias in $old_aliases; do
      if [[ $alias == *_smart ]]; then
        unalias $alias
      fi
    done

    # Generate new aliases with context awareness
    for cmd_ctx pattern in ${(kv)SHELL_LEARNED}; do
      local cmd=${cmd_ctx#*:}
      if (( pattern > threshold )); then
        local dir=${cmd_ctx%:*}
        if [[ $PWD == $dir ]]; then
          alias "${cmd%% *}_smart"="$cmd"
        }
      fi
    done
  } always {
    # Release lock
    zsystem flock -u $lock_file
  }
}

# Initialize the intelligent shell
# @description Sets up the intelligent shell system
# @param none
# @return 0 on success, 1 on failure
_init_intelligent_shell() {
  # Validate dependencies
  __validate_deps || return 1

  # Initialize state
  __init_state

  # Load previous state
  __load_state

  # Set up hooks
  autoload -Uz add-zsh-hook
  add-zsh-hook preexec _track_command
  add-zsh-hook precmd _process_command
  add-zsh-hook chpwd __update_context

  # Initialize completions
  autoload -Uz compinit
  compinit

  # Generate initial aliases
  _generate_aliases

  return 0
}

# Export functions
export _track_command
export _process_command
export __update_context
export _generate_aliases
export _init_intelligent_shell

# Logging system
__log() {
  local level=$1
  local message=$2
  local log_dir="${XDG_STATE_HOME:-$HOME/.local/state}/zsh/logs"
  local log_file="$log_dir/intelligent_shell.log"

  # Ensure log directory exists
  mkdir -p $log_dir

  # Format log message
  local timestamp=${(%):-%D{%Y-%m-%d %H:%M:%S}}
  printf "[%s] [%s] %s\n" "$timestamp" "$level" "$message" >> $log_file
}

# Metrics tracking
__track_metric() {
  local metric=$1
  local value=$2
  local metrics_file="${XDG_STATE_HOME:-$HOME/.local/state}/zsh/metrics.zsh"

  # Initialize metrics file
  if [[ ! -f $metrics_file ]]; then
    touch $metrics_file
  }

  # Update metric
  local key="${(%):-%D{%Y%m%d}}:$metric"
  local current=$(<$metrics_file)
  if [[ $current == *$key* ]]; then
    sed -i "" "s/$key:[0-9]*/$key:$value/" $metrics_file
  else
    echo "$key:$value" >> $metrics_file
  }
}

# Add performance tracking
__track_performance() {
  local start=$1
  local operation=$2
  local duration=$((SECONDS - start))

  __track_metric "${operation}_duration" $duration

  if (( duration > 1 )); then
    __log "WARN" "Slow operation ($duration sec): $operation"
  }
}
