# Environment Configuration Conflicts

## 1. Shell Framework Overlap

- Multiple ZSH frameworks detected:
  - zgenom (active)
  - zi (active)
  - oh-my-zsh (remnants)
  - Custom configurations

## 2. Version Manager Conflicts

- Multiple version managers present:
  - mise (2025.1.0) - Primary
  - nodenv (1.5.0)
  - pyenv (2.5.0)
  - rbenv (1.3.0)
  - asdf (not found, but referenced)

## 3. Configuration Fragmentation

### ZSH Config Files

- Multiple .zshrc backups:
  - .zshrc.backup-20241216
  - .zshrc.backup-20241217-022012
  - .zshrc.new
  - .zshrc.pre-oh-my-zsh
- Completion cache fragmentation:
  - Multiple .zcompdump files
  - Zwc compilation inconsistencies

### Dorothy Integration

Location: ~/.config/dorothy
Status: Active with local overrides
Conflicts:

- Command path overlap
- Configuration layering
- Local vs. Global settings

## 4. Critical Issues

### Version Management

1. mise vs. Traditional Managers
   - mise handles: python, node, ruby
   - Conflicts with: pyenv, nodenv, rbenv
   - Resolution needed for PATH precedence

### Shell Integration

1. Framework Conflicts
   - Multiple plugin managers
   - Duplicate initializations
   - Competing completions

### Path Resolution

1. Binary Conflicts
   - Multiple python versions
   - Competing node installations
   - Ruby version conflicts

## 5. Resolution Strategy

### Immediate Actions

1. Framework Consolidation

   ```bash
   # Choose primary framework (zi)
   # Remove others systematically
   mv ~/.zgenom ~/.zgenom.bak
   mv ~/.oh-my-zsh ~/.oh-my-zsh.bak
   ```

2. Version Manager Migration

   ```bash
   # Migrate to mise
   mise use --global python@3.13.1
   mise use --global node@latest
   mise use --global ruby@latest
   ```

3. Configuration Cleanup

   ```bash
   # Consolidate to XDG
   mkdir -p ~/.config/zsh
   # Move with backup
   for f in ~/.z*; do
     [[ -f $f ]] && cp $f ~/.config/zsh/
   done
   ```

### Long-term Strategy

1. Single Source of Truth
   - mise for runtime versions
   - zi for shell extensions
   - XDG compliance for configs

2. Dorothy Integration
   - Review command conflicts
   - Consolidate local overrides
   - Document integration points

## 6. Monitoring Points

- [ ] Shell startup time
- [ ] Command resolution paths
- [ ] Plugin load order
- [ ] Completion system health
- [ ] Environment variable conflicts
