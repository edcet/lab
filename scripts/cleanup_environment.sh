#!/bin/bash

# Exit on error
set -e

echo "Starting workspace cleanup..."

# Create clean directory structure
for dir in src/core src/external tests/unit tests/integration docs scripts config; do
    echo "Creating directory: $dir"
    mkdir -p "$dir"
done

# Function to safely move files
safe_move() {
    local src="$1"
    local dest="$2"
    if [ -f "$src" ]; then
        if [ -f "$dest/$(basename "$src")" ]; then
            echo "Warning: $dest/$(basename "$src") already exists, skipping..."
        else
            echo "Moving $src to $dest/"
            mv "$src" "$dest/"
        fi
    fi
}

# Move Python files to src
echo "Moving Python files to src/"
for file in *.py; do
    if [ -f "$file" ] && [ "$file" != "setup.py" ]; then
        safe_move "$file" "src"
    fi
done

# Move documentation
echo "Moving documentation to docs/"
for file in *.md; do
    if [ -f "$file" ] && [ "$file" != "README.md" ]; then
        safe_move "$file" "docs"
    fi
done

# Move configuration
echo "Moving configuration files to config/"
for file in .cursorrules .state_core; do
    safe_move "$file" "config"
done

# Clean up redundant directories
echo "Cleaning up redundant directories..."
for dir in organized_workspace organized build staging __pycache__ lab.egg-info .pytest_cache; do
    if [ -d "$dir" ]; then
        echo "Removing $dir/"
        rm -rf "$dir"
    fi
done

# Create .gitignore if it doesn't exist
if [ ! -f .gitignore ]; then
    echo "Creating .gitignore..."
    cat > .gitignore << 'EOL'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
.coverage
htmlcov/
.env
venv/
.vscode/
.idea/
EOL
fi

echo "Workspace cleanup complete"
