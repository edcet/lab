# Path Deduplication Analysis

## Current Issues

1. Duplicate Python deactivate paths:
   - Line 1, 4, 22: `/Users/him/.cursor/extensions/ms-python.python-2024.12.3-darwin-arm64/python_files/deactivate/zsh`

2. Duplicate venv paths:
   - Line 2, 5, 23: `/Users/him/lab/venv/bin`

3. Duplicate local bin:
   - Line 27, 28, 29: `/Users/him/.local/bin`

4. Duplicate Homebrew paths:
   - Line 3, 24: `/opt/homebrew/bin`

## Cleanup Plan

### 1. Immediate Actions

```bash
# Create new PATH with deduplicated entries
NEW_PATH=$(echo $PATH | tr ':' '\n' | awk '!seen[$0]++' | tr '\n' ':' | sed 's/:$//')

# Update PATH in shell configuration
cat >> ~/.config/zsh/path.zsh << 'EOF'
# Deduplicated PATH
export PATH="${NEW_PATH}"

# Ensure critical paths are first
path=(
  $HOME/.local/bin
  $HOME/lab/venv/bin
  /opt/homebrew/bin
  /opt/homebrew/sbin
  $path
)
typeset -U path
EOF
```

### 2. Priority Order

1. Local user binaries (~/.local/bin)
2. Project virtual environment
3. Homebrew
4. System paths
5. Application paths

### 3. Verification Steps

1. Check path uniqueness:

   ```bash
   echo $PATH | tr ':' '\n' | sort | uniq -d
   ```

2. Verify critical binaries:

   ```bash
   which -a python
   which -a pip
   which -a node
   ```

3. Test command resolution:

   ```bash
   type -a python
   type -a pip
   type -a node
   ```

## Monitoring

- Regular path audits
- Command resolution verification
- Performance impact assessment
