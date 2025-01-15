# Dry Run Verification Plan (M1 Max macOS Sequoia)

## 1. Environment Verification

\`\`\`bash

# Current State

arch: arm64
os: darwin 24.3.0
shell: /opt/homebrew/bin/zsh
python: 3.13.1
homebrew: /opt/homebrew (Apple Silicon)
\`\`\`

## 2. Proposed Changes Sequence

### Phase 1: Path Deduplication

\`\`\`bash

# Backup current PATH

echo $PATH > ~/.path.backup-$(date +%Y%m%d)

# Test new PATH construction

NEW_PATH_TEST=$(echo $PATH | tr ':' '\n' | awk '!seen[$0]++' | tr '\n' ':' | sed 's/:$//')

# Verify binary resolution remains correct

for cmd in python pip node zsh brew; do
    echo "=== $cmd ==="
    which -a $cmd
    type -a $cmd
done
\`\`\`

### Phase 2: XDG Compliance

\`\`\`bash

# Test XDG structure

mkdir -p ~/.config-test/{zsh,git,mise,starship}
mkdir -p ~/.local-test/{bin,share,state,cache}

# Verify no collisions

ls -la ~/.config-test
ls -la ~/.local-test
\`\`\`

### Phase 3: Tool Integration

\`\`\`bash

# Test endpoints without modifying

curl -I localhost:11434/api/health
curl -I localhost:1234/v1/chat/completions
curl -I localhost:4891/health
curl -I localhost:1337/health

# Verify binary paths

echo "=== Tool Binaries ==="
which -a ollama
which -a tgpt
which -a jan
\`\`\`

## 3. Rollback Plan

### Immediate Reversion

\`\`\`bash

# Path restoration

cp ~/.path.backup-$(date +%Y%m%d) ~/.path.current

# Structure reversion

rm -rf ~/.config-test
rm -rf ~/.local-test

# Tool configuration reset

brew services stop ollama
brew services stop tgpt
\`\`\`

## 4. Verification Points

### Critical Paths

- [ ] /opt/homebrew/bin (M1 specific)
- [ ] ~/.local/bin
- [ ] /Users/him/lab/venv/bin
- [ ] System paths (/usr/bin, /bin)

### Tool Dependencies

- [ ] Ollama: localhost:11434 (Active)
- [ ] LM Studio: localhost:1234 (Active)
- [ ] TGPT: localhost:4891 (Pending)
- [ ] Jan: localhost:1337 (Pending)

### M1 Specific

- [ ] Rosetta 2 compatibility
- [ ] ARM64 native binaries
- [ ] Universal binary handling

## 5. Success Criteria

1. All binaries resolve correctly
2. No duplicate paths
3. XDG compliance maintained
4. Tool endpoints accessible
5. No performance regression

```
