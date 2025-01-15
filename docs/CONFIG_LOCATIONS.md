# Configuration File Locations & Relationships

## 1. Core Configuration Directories

### XDG Base

- ~/.config/
- ~/.local/share/
- ~/.local/state/
- ~/.cache/

### Shell Configuration

- ~/.config/zsh/
- ~/.config/fish/
- /opt/homebrew/etc/profile.d/
- /opt/homebrew/etc/bash_completion.d/

### Tool Configuration

1. Development Tools
   - ~/.config/raycast/
   - ~/.config/lvim/
   - ~/.config/kitty/
   - ~/.local/share/lunarvim/

2. Environment Management
   - ~/.config/mise/
   - /opt/homebrew/etc/pyenv.d/
   - /opt/homebrew/etc/rbenv.d/

3. AI Integration
   - ~/.config/ollama/
   - ~/.config/tgpt/
   - ~/.local/share/gpt4all.io/

## 2. Backup Locations

### System Backups

- ~/.local/share/backups/20241231_203750/
  - Configuration backups
  - Tool settings
  - Shell configurations

### Application Backups

- ~/.config/raycast/extensions/
- ~/.config/zsh/.zi/bin/
- ~/.local/share/lunarvim/site/

## 3. Integration Points

### Shell Framework

1. ZI Configuration

   ```bash
   ~/.config/zsh/.zi/bin/
   ~/.config/zsh/.zi/plugins/
   ```

2. Environment Modules

   ```bash
   /opt/homebrew/etc/modulefiles/
   /opt/homebrew/etc/profile.d/
   ```

### Development Environment

1. Python Setup

   ```bash
   ~/.local/share/virtualenvs/
   /opt/homebrew/etc/pyenv.d/
   ```

2. Ruby Setup

   ```bash
   /opt/homebrew/etc/rbenv.d/
   ~/.config/mise/ruby/
   ```

### Tool Integration

1. AI Tools

   ```bash
   ~/.config/ollama/
   ~/.config/tgpt/
   ~/.local/share/gpt4all.io/
   ```

2. Editor Configuration

   ```bash
   ~/.config/lvim/
   ~/.local/share/lunarvim/
   ```

## 4. Monitoring Points

### Health Checks

- [ ] XDG compliance
- [ ] Backup integrity
- [ ] Configuration synchronization
- [ ] Tool accessibility

### Integration Status

- [ ] Shell framework
- [ ] Development environment
- [ ] AI tools
- [ ] Editor setup

## 5. Relationships

### Primary Dependencies

1. Shell → Environment
   - ZSH configuration depends on XDG
   - Environment modules depend on shell

2. Tools → Configuration
   - AI tools depend on shell environment
   - Development tools depend on XDG

### Secondary Dependencies

1. Backup → Recovery
   - Configuration backups
   - Tool settings preservation
   - Shell state maintenance

2. Integration → Coordination
   - Shell framework plugins
   - Tool interoperability
   - Environment synchronization
