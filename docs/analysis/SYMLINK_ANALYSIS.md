# Symlink Analysis & Cleanup Plan

## 1. Current State

### Shell Configuration Symlinks

- Multiple .zshrc backups identified
- Fragmented configuration files
- Mixed XDG and home directory usage

### Binary Symlinks (~/.local/bin)

- pipx installations (33 symlinks)
- Application binaries (Q, Fig)
- Development tools (pylsp, interpreter)

### Tool-specific Symlinks

- Git configuration
- Python virtual environments
- Application configurations

## 2. Cleanup Actions

### Immediate Tasks

1. Consolidate shell configurations:

   ```bash
   # Move to XDG structure
   mkdir -p ~/.config/zsh
   mv ~/.z* ~/.config/zsh/
   ln -sf ~/.config/zsh/.zshrc ~/.zshrc
   ```

2. Standardize binary locations:

   ```bash
   # Verify and repair pipx symlinks
   pipx reinstall-all
   # Update application symlinks
   ln -sf /Applications/*/Contents/MacOS/* ~/.local/bin/
   ```

3. Clean backup pollution:

   ```bash
   # Archive old backups
   mkdir -p ~/.local/backup/zsh
   mv ~/.z*.bak ~/.local/backup/zsh/
   ```

### Monitoring Points

- Symlink integrity
- Path resolution
- Application accessibility

## 3. Integration Status

### Verified Links

- Git configuration
- Python environment
- Shell configuration

### Pending Verification

- Application binaries
- Development tools
- Configuration files

## 4. Maintenance Plan

- Regular symlink verification
- Automated cleanup
- Documentation updates
