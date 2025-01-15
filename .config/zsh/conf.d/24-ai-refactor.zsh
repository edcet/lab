#!/usr/bin/env zsh

# AI Refactoring System
# Intelligent code improvement suggestions

function aiops_refactor() {
    local target="${1:-.}"
    local mode="${2:-suggest}"  # suggest or apply

    __ensure_aiops_components || return $?

    print -P "%F{blue}AI Refactoring Analysis%f"

    python3 - << 'EOL'
import sys
from pathlib import Path
import ast
import libcst as cst
from typing import Dict, List, Any
import re

class RefactoringVisitor(ast.NodeVisitor):
    def __init__(self):
        self.suggestions = []
        self.current_function = None
        self.current_class = None

    def visit_FunctionDef(self, node):
        self.current_function = node.name

        # Check function length
        if len(node.body) > 20:
            self.suggestions.append({
                'type': 'function_length',
                'location': f'Function {node.name}',
                'suggestion': 'Consider breaking down into smaller functions',
                'complexity': 'high'
            })

        # Check parameter count
        if len(node.args.args) > 5:
            self.suggestions.append({
                'type': 'parameter_count',
                'location': f'Function {node.name}',
                'suggestion': 'Consider using a dataclass or grouping related parameters',
                'complexity': 'medium'
            })

        self.generic_visit(node)
        self.current_function = None

    def visit_ClassDef(self, node):
        self.current_class = node.name

        # Check for missing docstring
        if not ast.get_docstring(node):
            self.suggestions.append({
                'type': 'missing_docstring',
                'location': f'Class {node.name}',
                'suggestion': 'Add class documentation',
                'complexity': 'low'
            })

        # Check for too many methods
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        if len(methods) > 10:
            self.suggestions.append({
                'type': 'class_size',
                'location': f'Class {node.name}',
                'suggestion': 'Consider splitting into smaller classes',
                'complexity': 'high'
            })

        self.generic_visit(node)
        self.current_class = None

    def visit_If(self, node):
        # Check for nested if statements
        nested_ifs = len([n for n in ast.walk(node) if isinstance(n, ast.If)])
        if nested_ifs > 3:
            self.suggestions.append({
                'type': 'nested_conditionals',
                'location': f'{"Class " + self.current_class if self.current_class else ""} {"Function " + self.current_function if self.current_function else ""}',
                'suggestion': 'Consider using early returns or guard clauses',
                'complexity': 'medium'
            })
        self.generic_visit(node)

def analyze_code_style(code: str) -> List[Dict[str, str]]:
    """Analyze code style and suggest improvements"""
    suggestions = []

    # Check line length
    for i, line in enumerate(code.splitlines(), 1):
        if len(line) > 88:
            suggestions.append({
                'type': 'line_length',
                'location': f'Line {i}',
                'suggestion': 'Consider breaking into multiple lines',
                'complexity': 'low'
            })

    # Check import style
    import_lines = [line for line in code.splitlines() if line.startswith('import') or line.startswith('from')]
    if not all(sorted(import_lines) == import_lines):
        suggestions.append({
            'type': 'import_order',
            'location': 'Import section',
            'suggestion': 'Sort imports alphabetically',
            'complexity': 'low'
        })

    return suggestions

def analyze_naming(code: str) -> List[Dict[str, str]]:
    """Analyze naming conventions"""
    suggestions = []

    # Function naming
    function_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    for match in re.finditer(function_pattern, code):
        name = match.group(1)
        if not name.islower() or '_' not in name:
            suggestions.append({
                'type': 'function_naming',
                'location': f'Function {name}',
                'suggestion': 'Use snake_case for function names',
                'complexity': 'low'
            })

    # Class naming
    class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    for match in re.finditer(class_pattern, code):
        name = match.group(1)
        if not name[0].isupper() or '_' in name:
            suggestions.append({
                'type': 'class_naming',
                'location': f'Class {name}',
                'suggestion': 'Use PascalCase for class names',
                'complexity': 'low'
            })

    return suggestions

def analyze_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a single file and generate refactoring suggestions"""
    try:
        code = file_path.read_text()
        tree = ast.parse(code)

        # Collect suggestions
        visitor = RefactoringVisitor()
        visitor.visit(tree)

        suggestions = (
            visitor.suggestions +
            analyze_code_style(code) +
            analyze_naming(code)
        )

        return {
            'path': str(file_path),
            'suggestions': suggestions
        }
    except Exception as e:
        return {'path': str(file_path), 'error': str(e)}

def main():
    target = Path(sys.argv[1])
    mode = sys.argv[2]

    if target.is_file():
        files = [target]
    else:
        files = list(target.rglob('*.py'))

    total_suggestions = 0

    for file in files:
        result = analyze_file(file)
        if 'error' not in result:
            suggestions = result['suggestions']
            if suggestions:
                print(f"\n\033[33m{file.relative_to(target)}\033[0m")

                # Group suggestions by complexity
                by_complexity = {'high': [], 'medium': [], 'low': []}
                for suggestion in suggestions:
                    by_complexity[suggestion['complexity']].append(suggestion)

                # Print suggestions by priority
                for complexity in ['high', 'medium', 'low']:
                    if by_complexity[complexity]:
                        print(f"\n{complexity.upper()} Priority:")
                        for suggestion in by_complexity[complexity]:
                            print(f"- [{suggestion['type']}] {suggestion['location']}")
                            print(f"  Suggestion: {suggestion['suggestion']}")

                total_suggestions += len(suggestions)
        else:
            print(f"\n\033[31mError analyzing {file}: {result['error']}\033[0m")

    # Summary
    print(f"\n\033[34mSummary: Found {total_suggestions} potential improvements\033[0m")

    if mode == 'apply' and total_suggestions > 0:
        print("\n\033[33mAutomatic refactoring is not yet implemented\033[0m")
        print("Please review suggestions and apply them manually")

if __name__ == '__main__':
    main()
EOL "$target" "$mode"
}

# Register command
alias airef='aiops_refactor'

# Command completion
compdef _aiops_commands airef

# Update help
function aiops_help() {
    print -P "%F{blue}AI Operations Commands:%f"
    print -P "  airev     - Run AI code review"
    print -P "  aideps    - Analyze dependencies"
    print -P "  aiperf    - Analyze performance"
    print -P "  aidocs    - Analyze documentation"
    print -P "  airef     - Get refactoring suggestions"
}
