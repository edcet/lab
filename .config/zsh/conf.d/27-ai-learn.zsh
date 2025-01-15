#!/usr/bin/env zsh

# AI Learning System
# Pattern recognition and adaptive suggestions

function aiops_learn() {
    local action="$1"
    local target="${2:-.}"

    __ensure_aiops_components || return $?

    case "$action" in
        analyze)
            print -P "%F{blue}Analyzing Development Patterns%f"
            python3 - << 'EOL'
import sys
from pathlib import Path
import json
import ast
from typing import Dict, List, Any
from collections import defaultdict
import numpy as np
from datetime import datetime, timezone
import pickle
import re

class PatternLearner:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.patterns_dir = repo_path / '.ai' / 'patterns'
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_file = self.patterns_dir / 'learned_patterns.pkl'
        self.load_patterns()

    def load_patterns(self):
        """Load existing patterns"""
        if self.patterns_file.exists():
            with open(self.patterns_file, 'rb') as f:
                self.patterns = pickle.load(f)
        else:
            self.patterns = {
                'code_structure': defaultdict(list),
                'naming_conventions': defaultdict(list),
                'error_handling': defaultdict(list),
                'test_patterns': defaultdict(list),
                'documentation': defaultdict(list),
                'performance': defaultdict(list)
            }

    def save_patterns(self):
        """Save learned patterns"""
        with open(self.patterns_file, 'wb') as f:
            pickle.dump(self.patterns, f)

    def analyze_code_structure(self, node: ast.AST) -> Dict[str, Any]:
        """Analyze code structure patterns"""
        patterns = defaultdict(int)

        for child in ast.walk(node):
            if isinstance(child, ast.FunctionDef):
                # Function complexity patterns
                patterns['avg_function_length'] += len(child.body)
                patterns['function_count'] += 1
                patterns['param_count'] += len(child.args.args)

                # Return patterns
                returns = len([n for n in ast.walk(child) if isinstance(n, ast.Return)])
                patterns['return_points'] += returns

                # Error handling patterns
                try_blocks = len([n for n in ast.walk(child) if isinstance(n, ast.Try)])
                patterns['error_handling'] += try_blocks

            elif isinstance(child, ast.ClassDef):
                # Class structure patterns
                patterns['class_count'] += 1
                methods = len([n for n in child.body if isinstance(n, ast.FunctionDef)])
                patterns['avg_methods_per_class'] += methods

        if patterns['function_count'] > 0:
            patterns['avg_function_length'] /= patterns['function_count']
            patterns['avg_params'] = patterns['param_count'] / patterns['function_count']

        if patterns['class_count'] > 0:
            patterns['avg_methods_per_class'] /= patterns['class_count']

        return dict(patterns)

    def analyze_naming_patterns(self, code: str) -> Dict[str, List[str]]:
        """Analyze naming conventions"""
        patterns = {
            'function_names': [],
            'class_names': [],
            'variable_names': []
        }

        # Extract names using regex
        patterns['function_names'] = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
        patterns['class_names'] = re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
        patterns['variable_names'] = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=', code)

        return patterns

    def analyze_error_patterns(self, node: ast.AST) -> Dict[str, Any]:
        """Analyze error handling patterns"""
        patterns = defaultdict(int)

        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                patterns['try_blocks'] += 1
                patterns['except_handlers'] += len(child.handlers)
                patterns['has_finally'] += 1 if child.finalbody else 0
                patterns['has_else'] += 1 if child.orelse else 0

                # Analyze exception types
                for handler in child.handlers:
                    if handler.type:
                        exc_name = handler.type.id if isinstance(handler.type, ast.Name) else str(handler.type)
                        patterns[f'exception_{exc_name}'] += 1

        return dict(patterns)

    def analyze_test_patterns(self, code: str) -> Dict[str, Any]:
        """Analyze testing patterns"""
        patterns = defaultdict(int)

        # Find test functions and their patterns
        test_funcs = re.finditer(r'def\s+(test_[a-zA-Z0-9_]*)', code)
        for match in test_funcs:
            patterns['test_count'] += 1
            func_name = match.group(1)

            # Analyze test naming patterns
            if 'test_should' in func_name:
                patterns['behavior_tests'] += 1
            elif 'test_when' in func_name:
                patterns['conditional_tests'] += 1
            elif 'test_edge' in func_name:
                patterns['edge_case_tests'] += 1

        # Find assertion patterns
        patterns['assertions'] = len(re.findall(r'assert\s+', code))
        patterns['assert_equal'] = len(re.findall(r'assertEqual|assert_equal', code))
        patterns['assert_raises'] = len(re.findall(r'assertRaises|assert_raises', code))

        return dict(patterns)

    def analyze_documentation_patterns(self, node: ast.AST) -> Dict[str, Any]:
        """Analyze documentation patterns"""
        patterns = defaultdict(int)

        for child in ast.walk(node):
            if isinstance(child, (ast.FunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(child)
                if docstring:
                    patterns['has_docstring'] += 1
                    # Analyze docstring patterns
                    if 'Args:' in docstring:
                        patterns['args_section'] += 1
                    if 'Returns:' in docstring:
                        patterns['returns_section'] += 1
                    if 'Raises:' in docstring:
                        patterns['raises_section'] += 1
                    if 'Example:' in docstring:
                        patterns['example_section'] += 1

            if isinstance(child, ast.FunctionDef):
                # Type hint patterns
                if child.returns:
                    patterns['return_type_hints'] += 1
                patterns['param_type_hints'] += sum(1 for arg in child.args.args if arg.annotation)

        return dict(patterns)

    def learn_from_file(self, file_path: Path) -> Dict[str, Any]:
        """Learn patterns from a single file"""
        try:
            code = file_path.read_text()
            tree = ast.parse(code)

            file_patterns = {
                'code_structure': self.analyze_code_structure(tree),
                'naming': self.analyze_naming_patterns(code),
                'error_handling': self.analyze_error_patterns(tree),
                'testing': self.analyze_test_patterns(code),
                'documentation': self.analyze_documentation_patterns(tree)
            }

            # Update global patterns
            for category, patterns in file_patterns.items():
                if isinstance(patterns, dict):
                    for pattern, value in patterns.items():
                        self.patterns[category][pattern].append(value)

            return file_patterns

        except Exception as e:
            return {'error': str(e)}

    def generate_insights(self) -> Dict[str, Any]:
        """Generate insights from learned patterns"""
        insights = {
            'code_structure': {},
            'naming': {},
            'error_handling': {},
            'testing': {},
            'documentation': {},
            'recommendations': []
        }

        # Analyze code structure patterns
        if self.patterns['code_structure']:
            for metric, values in self.patterns['code_structure'].items():
                if values:
                    avg = np.mean(values)
                    std = np.std(values)
                    insights['code_structure'][metric] = {
                        'average': avg,
                        'std': std,
                        'trend': 'increasing' if len(values) > 1 and values[-1] > avg else 'stable'
                    }

        # Analyze naming conventions
        if self.patterns['naming_conventions']:
            naming_patterns = defaultdict(int)
            for names in self.patterns['naming_conventions'].values():
                for name in names:
                    if '_' in name:
                        naming_patterns['snake_case'] += 1
                    elif name[0].isupper():
                        naming_patterns['pascal_case'] += 1
                    elif name[0].islower() and any(c.isupper() for c in name[1:]):
                        naming_patterns['camel_case'] += 1
            insights['naming'] = dict(naming_patterns)

        # Generate recommendations
        if insights['code_structure']:
            if insights['code_structure'].get('avg_function_length', {}).get('average', 0) > 20:
                insights['recommendations'].append({
                    'type': 'code_structure',
                    'message': 'Consider breaking down long functions',
                    'priority': 'high'
                })

        if insights['documentation']:
            doc_coverage = insights['documentation'].get('has_docstring', 0) / max(
                insights['code_structure'].get('function_count', 1), 1)
            if doc_coverage < 0.8:
                insights['recommendations'].append({
                    'type': 'documentation',
                    'message': 'Improve documentation coverage',
                    'priority': 'medium'
                })

        return insights

def main():
    repo_path = Path(sys.argv[1])
    learner = PatternLearner(repo_path)

    print("\033[34mAnalyzing development patterns...\033[0m")

    # Process Python files
    for file in repo_path.rglob('*.py'):
        if 'test' not in file.name:
            print(f"\nAnalyzing {file.relative_to(repo_path)}")
            patterns = learner.learn_from_file(file)
            if 'error' not in patterns:
                print("✓ Patterns extracted")
            else:
                print(f"✗ Error: {patterns['error']}")

    # Save learned patterns
    learner.save_patterns()

    # Generate insights
    insights = learner.generate_insights()

    # Print insights
    print("\n\033[34mDevelopment Insights:\033[0m")

    if insights['code_structure']:
        print("\nCode Structure Patterns:")
        for metric, stats in insights['code_structure'].items():
            print(f"- {metric}: {stats['average']:.2f} (±{stats['std']:.2f}) [{stats['trend']}]")

    if insights['naming']:
        print("\nNaming Conventions:")
        total = sum(insights['naming'].values())
        for style, count in insights['naming'].items():
            percentage = (count / total * 100) if total > 0 else 0
            print(f"- {style}: {percentage:.1f}%")

    if insights['recommendations']:
        print("\nRecommendations:")
        for rec in insights['recommendations']:
            print(f"[{rec['priority'].upper()}] {rec['message']}")

if __name__ == '__main__':
    main()
EOL "$target"
            ;;

        adapt)
            print -P "%F{blue}Adapting to Patterns%f"
            python3 - << 'EOL'
import sys
from pathlib import Path
import pickle
import json
from typing import Dict, Any
import numpy as np

def load_patterns(patterns_file: Path) -> Dict[str, Any]:
    """Load learned patterns"""
    if patterns_file.exists():
        with open(patterns_file, 'rb') as f:
            return pickle.load(f)
    return {}

def adapt_configurations(patterns: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt configurations based on learned patterns"""
    configs = {
        'code_style': {},
        'test_generation': {},
        'documentation': {},
        'refactoring': {}
    }

    # Adapt code style preferences
    if 'code_structure' in patterns:
        structure = patterns['code_structure']
        if 'avg_function_length' in structure:
            lengths = structure['avg_function_length']
            configs['code_style']['max_function_length'] = int(np.mean(lengths) + np.std(lengths))

    # Adapt test generation
    if 'test_patterns' in patterns:
        test_patterns = patterns['test_patterns']
        configs['test_generation'] = {
            'generate_edge_cases': any('edge_case' in p for p in test_patterns),
            'assertion_style': 'assert_equal' if test_patterns.get('assert_equal', 0) > test_patterns.get('assertions', 0) / 2 else 'assert',
            'include_property_tests': any('property' in p for p in test_patterns)
        }

    # Adapt documentation requirements
    if 'documentation' in patterns:
        docs = patterns['documentation']
        configs['documentation'] = {
            'require_docstrings': sum(docs.values()) > 0,
            'docstring_style': 'google' if docs.get('args_section', 0) > 0 else 'simple',
            'require_type_hints': docs.get('param_type_hints', 0) > 0
        }

    return configs

def main():
    repo_path = Path(sys.argv[1])
    patterns_file = repo_path / '.ai' / 'patterns' / 'learned_patterns.pkl'

    if not patterns_file.exists():
        print("\033[31mNo learned patterns found. Run 'aiops learn analyze' first.\033[0m")
        return

    print("\033[34mAdapting to development patterns...\033[0m")

    # Load patterns and adapt
    patterns = load_patterns(patterns_file)
    configs = adapt_configurations(patterns)

    # Save adapted configurations
    config_file = repo_path / '.ai' / 'config.json'
    with open(config_file, 'w') as f:
        json.dump(configs, f, indent=2)

    # Print adaptations
    print("\n\033[34mAdapted Configurations:\033[0m")

    if 'code_style' in configs:
        print("\nCode Style:")
        for key, value in configs['code_style'].items():
            print(f"- {key}: {value}")

    if 'test_generation' in configs:
        print("\nTest Generation:")
        for key, value in configs['test_generation'].items():
            print(f"- {key}: {value}")

    if 'documentation' in configs:
        print("\nDocumentation:")
        for key, value in configs['documentation'].items():
            print(f"- {key}: {value}")

    print(f"\nConfigurations saved to {config_file}")

if __name__ == '__main__':
    main()
EOL "$target"
            ;;

        *)
            print -P "%F{red}Unknown action: $action%f"
            print -P "Try: analyze, adapt"
            return 1
            ;;
    esac
}

# Register command
alias ailearn='aiops_learn'

# Command completion
compdef _aiops_commands ailearn

# Update help
function aiops_help() {
    print -P "%F{blue}AI Operations Commands:%f"
    print -P "  airev     - Run AI code review"
    print -P "  aideps    - Analyze dependencies"
    print -P "  aiperf    - Analyze performance"
    print -P "  aidocs    - Analyze documentation"
    print -P "  airef     - Get refactoring suggestions"
    print -P "  aitest    - Generate test cases"
    print -P "  aimet     - Collect and visualize metrics"
    print -P "  ailearn   - Learn and adapt to patterns"
}
