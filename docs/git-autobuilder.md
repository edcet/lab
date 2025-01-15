# Git Autobuilder

Automated git operations with intelligent commit management and GitHub integration.

## Features

- 🤖 AI-powered commit messages and code reviews
- 🧠 Smart conflict resolution
- 🔄 Intelligent branch management
- 🌐 GitHub integration with PR creation
- 🪝 Secure webhook support
- 📊 Advanced build status tracking
- 🚀 Automated releases with changelogs

## Quick Start

1. Configure GitHub credentials:
   ```bash
   export GITHUB_TOKEN="your-token"
   export GITHUB_REPOSITORY="username/repo"
   export WEBHOOK_URL="your-webhook-url"
   export WEBHOOK_SECRET="your-webhook-secret"
   ```

2. Use automated git commands:
   ```bash
   # Auto-commit changes with AI-enhanced message
   gac "optional message"

   # Auto-push changes to GitHub
   gap

   # Create feature branch with AI-suggested name and PR
   gapr "feature-name"

   # Get AI code review
   grv

   # Smart conflict resolution
   grs "conflicted-file.txt" semantic

   # Watch directory with auto-review
   gw . 300 true true
   ```

## Configuration

The Git autobuilder can be configured through `~/.config/git-autobuilder/config.toml`:

```toml
[github]
username = "your-username"
token = "your-token"
default_repo = "your-repo"

[commit]
types = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "test",
    "chore"
]
scopes = [
    "core",
    "ui",
    "docs",
    "tests",
    "config"
]

[ai]
enhance_commits = true
suggest_branches = true
review_code = true
resolve_conflicts = true

[security]
sign_webhooks = true
verify_commits = true
scan_secrets = true
```

## AI-Powered Features

### Smart Commit Messages

The autobuilder uses AI to enhance commit messages:
```bash
# Original message
gac "update code"

# AI-enhanced message
feat(api): implement user authentication with OAuth2 support
```

### Intelligent Code Review

Get AI-powered code reviews:
```bash
# Review current changes
grv

# Review specific directory
grv src/

# Review with auto-fix suggestions
grv --fix
```

### Smart Conflict Resolution

Three-level conflict resolution:
1. **Semantic**: AI-powered intelligent merging
2. **Auto**: Git's built-in resolution
3. **Interactive**: Visual merge tool

```bash
# Try semantic resolution first
grs "conflicted-file.txt" semantic

# Fall back to automatic
grs "conflicted-file.txt" auto

# Use interactive tool
grs "conflicted-file.txt" interactive
```

### Branch Management

AI-powered branch naming and management:
```bash
# Create branch with AI-suggested name
gsb

# Create specific feature branch
gsb "auth-feature"

# List managed branches
git branch --list "feature/*"
```

## Workspace Management

### Initialize Workspace
```bash
# Create new workspace
gwi ~/projects/new-project

# Initialize with template
gwi ~/projects/new-project --template python
```

### Scan Workspace
```bash
# Scan for repositories
gws ~/projects

# Deep scan with custom depth
gws ~/projects 5
```

### Monitor Workspace
```bash
# Monitor all repositories
gwm ~/projects

# Monitor with custom interval
gwm ~/projects 60  # 1-minute interval
```

## GitHub Actions Integration

The autobuilder includes an enhanced GitHub Actions workflow:

### Automated Analysis
- AI code review on PRs
- Security scanning
- Change impact assessment
- Dependency verification

### Smart Builds
- Conditional test execution
- Coverage reporting
- Documentation generation
- Security scanning

### Intelligent Releases
- Automated changelog generation
- Smart version numbering
- Release notes generation
- Asset bundling

Enable by adding secrets:
- `GITHUB_TOKEN`
- `WEBHOOK_URL`
- `WEBHOOK_SECRET`

## Advanced Usage

### Watch Mode with AI

Monitor directory with intelligent automation:
```bash
# Watch with AI review and auto-push
gw . 300 true true

# Watch multiple directories
for dir in */; do
    gw "$dir" 300 true true &
done
```

### Custom Workflows

Create custom automation workflows:
```bash
# Review and auto-fix
grv --fix && gac "fix: address review comments"

# Branch and PR
gsb "feature" && gapr

# Monitor and sync
gwm . && gap
```

## Security Features

### Webhook Security
- Payload signing
- Secret rotation
- Rate limiting
- IP allowlisting

### Code Security
- Secret scanning
- Dependency auditing
- Commit signing
- Access control

### Best Practices
1. **Environment Variables**
   - Use secure storage
   - Rotate regularly
   - Scope appropriately

2. **Webhooks**
   - Verify signatures
   - Use HTTPS only
   - Implement retry logic

3. **Automation**
   - Review AI suggestions
   - Monitor auto-commits
   - Audit automation logs

## Troubleshooting

### Common Issues

1. **AI Integration**
   ```bash
   # Verify GitHub Copilot access
   gh auth status
   gh copilot status
   ```

2. **Webhook Issues**
   ```bash
   # Test webhook with signature
   setup_github_hooks "$GITHUB_REPOSITORY" --verify
   ```

3. **Build Issues**
   ```bash
   # Check GitHub Actions logs
   gh run list
   gh run view
   ```

### Logs and Monitoring

Access detailed logs:
```bash
# View automation logs
tail -f ~/.local/share/git-autobuilder/logs/automation.log

# View AI suggestions
tail -f ~/.local/share/git-autobuilder/logs/ai.log

# View webhook events
tail -f ~/.local/share/git-autobuilder/logs/webhooks.log
```

## Contributing

1. **Setup Development Environment**
   ```bash
   gwi ~/projects/git-autobuilder
   gac "feat: initial commit"
   gapr "setup"
   ```

2. **Run Tests**
   ```bash
   mise exec -- pytest
   ```

3. **Submit Changes**
   ```bash
   grv --fix  # Get AI review
   gac "feat: new feature"
   gapr "feature"  # Creates PR with AI-enhanced title
   ```

## Security

The autobuilder includes comprehensive security features:
- AI-powered secret detection
- Secure token handling
- Signed webhooks
- Access control
- Audit logging

Always:
- Use environment variables
- Review AI suggestions
- Monitor automation
- Audit webhook activity
- Rotate secrets regularly
