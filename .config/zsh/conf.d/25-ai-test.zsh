#!/usr/bin/env zsh

# AI Test Generation System
# Automatic test case generation

function aiops_test() {
    local target="${1:-.}"
    local mode="${2:-generate}"  # generate or run

    __ensure_aiops_components || return $?

    print -P "%F{blue}AI Test Generation%f"

    python3 - << 'EOL'
import sys
from pathlib import Path
import ast
import inspect
from typing import Dict, List, Any, Optional
import re
import pytest
import hypothesis
from hypothesis import strategies as st

class TestGenerator(ast.NodeVisitor):
    def __init__(self):
        self.test_cases = []
        self.current_class = None

    def visit_FunctionDef(self, node):
        # Skip test functions
        if node.name.startswith('test_'):
            return

        # Generate test cases
        test_cases = self._generate_test_cases(node)
        self.test_cases.extend(test_cases)

    def _generate_test_cases(self, node) -> List[Dict[str, Any]]:
        """Generate test cases for a function"""
        cases = []

        # Basic test case
        cases.append({
            'type': 'basic',
            'function': node.name,
            'class': self.current_class,
            'params': self._analyze_parameters(node),
            'returns': self._analyze_return_type(node)
        })

        # Edge cases
        cases.extend(self._generate_edge_cases(node))

        # Property-based tests
        if self._can_generate_properties(node):
            cases.append({
                'type': 'property',
                'function': node.name,
                'class': self.current_class,
                'properties': self._generate_properties(node)
            })

        return cases

    def _analyze_parameters(self, node) -> List[Dict[str, Any]]:
        """Analyze function parameters"""
        params = []

        for arg in node.args.args:
            param = {
                'name': arg.arg,
                'type': self._get_annotation_name(arg.annotation) if arg.annotation else None
            }

            # Generate test values based on type
            param['test_values'] = self._generate_test_values(param['type'])
            params.append(param)

        return params

    def _analyze_return_type(self, node) -> Optional[str]:
        """Analyze function return type"""
        if node.returns:
            return self._get_annotation_name(node.returns)
        return None

    def _get_annotation_name(self, node) -> Optional[str]:
        """Get the name of a type annotation"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Subscript):
            return f"{self._get_annotation_name(node.value)}[{self._get_annotation_name(node.slice)}]"
        return None

    def _generate_test_values(self, type_name: Optional[str]) -> List[Any]:
        """Generate test values based on type"""
        if not type_name:
            return [None, 42, "", [], {}]

        basic_values = {
            'str': ['', 'test', 'a' * 1000],
            'int': [0, 1, -1, 2**31-1, -2**31],
            'float': [0.0, 1.0, -1.0, float('inf'), float('-inf')],
            'bool': [True, False],
            'list': [[], [1], [1, 2, 3]],
            'dict': [{}, {'a': 1}, {'a': 1, 'b': 2}],
            'tuple': [(), (1,), (1, 2, 3)],
            'set': [set(), {1}, {1, 2, 3}]
        }

        return basic_values.get(type_name, [None])

    def _generate_edge_cases(self, node) -> List[Dict[str, Any]]:
        """Generate edge cases"""
        cases = []

        # None values
        cases.append({
            'type': 'edge',
            'function': node.name,
            'class': self.current_class,
            'description': 'None values',
            'params': [{'name': p.arg, 'value': None} for p in node.args.args]
        })

        # Empty containers
        cases.append({
            'type': 'edge',
            'function': node.name,
            'class': self.current_class,
            'description': 'Empty containers',
            'params': [{'name': p.arg, 'value': self._get_empty_value(p.annotation)} for p in node.args.args]
        })

        return cases

    def _get_empty_value(self, annotation) -> Any:
        """Get empty value for a type"""
        if not annotation:
            return None

        type_name = self._get_annotation_name(annotation)
        empty_values = {
            'str': '',
            'list': [],
            'dict': {},
            'tuple': (),
            'set': set()
        }

        return empty_values.get(type_name, None)

    def _can_generate_properties(self, node) -> bool:
        """Check if we can generate property-based tests"""
        return bool(node.args.args) and bool(node.returns)

    def _generate_properties(self, node) -> List[Dict[str, Any]]:
        """Generate property-based tests"""
        properties = []

        # Invariant properties
        properties.append({
            'type': 'invariant',
            'description': 'Output type matches return annotation',
            'strategy': self._get_hypothesis_strategy(node.returns)
        })

        # Input-output relationships
        for arg in node.args.args:
            if arg.annotation:
                properties.append({
                    'type': 'relationship',
                    'description': f'Output depends on {arg.arg}',
                    'param': arg.arg,
                    'strategy': self._get_hypothesis_strategy(arg.annotation)
                })

        return properties

    def _get_hypothesis_strategy(self, annotation) -> Optional[str]:
        """Get Hypothesis strategy for a type"""
        if not annotation:
            return None

        type_name = self._get_annotation_name(annotation)
        strategies = {
            'str': 'st.text()',
            'int': 'st.integers()',
            'float': 'st.floats()',
            'bool': 'st.booleans()',
            'list': 'st.lists(st.integers())',
            'dict': 'st.dictionaries(st.text(), st.integers())',
            'tuple': 'st.tuples(st.integers())',
            'set': 'st.sets(st.integers())'
        }

        return strategies.get(type_name)

def generate_test_file(source_path: Path, test_cases: List[Dict[str, Any]]) -> str:
    """Generate test file content"""
    imports = [
        'import pytest',
        'from hypothesis import given, strategies as st',
        f'from {source_path.stem} import *\n'
    ]

    test_functions = []

    for case in test_cases:
        if case['type'] == 'basic':
            func_name = case['function']
            class_name = case['class']

            for params in _generate_param_combinations(case['params']):
                param_str = ', '.join(f'{p["name"]}={repr(p["value"])}' for p in params)
                expected = '...'  # Placeholder for expected value

                test = f"""
def test_{func_name}_{'_'.join(str(p['value']) for p in params)}():
    {'result = ' if case['returns'] else ''}{f'{class_name}().' if class_name else ''}{func_name}({param_str})
    {'assert result == ' + repr(expected) if case['returns'] else ''}
"""
                test_functions.append(test)

        elif case['type'] == 'edge':
            func_name = case['function']
            class_name = case['class']

            test = f"""
def test_{func_name}_{case['description'].lower().replace(' ', '_')}():
    {'result = ' if case['returns'] else ''}{f'{class_name}().' if class_name else ''}{func_name}({
        ', '.join(f'{p["name"]}={repr(p["value"])}' for p in case['params'])
    })
"""
            test_functions.append(test)

        elif case['type'] == 'property':
            func_name = case['function']
            class_name = case['class']

            for prop in case['properties']:
                if prop['type'] == 'invariant':
                    test = f"""
@given({prop['strategy']})
def test_{func_name}_invariant(value):
    result = {f'{class_name}().' if class_name else ''}{func_name}(value)
    assert isinstance(result, {case['returns']})
"""
                    test_functions.append(test)

                elif prop['type'] == 'relationship':
                    test = f"""
@given({prop['strategy']})
def test_{func_name}_{prop['param']}_relationship(value):
    result1 = {f'{class_name}().' if class_name else ''}{func_name}(value)
    result2 = {f'{class_name}().' if class_name else ''}{func_name}(value)
    assert result1 == result2  # Function should be deterministic
"""
                    test_functions.append(test)

    return '\n'.join(imports + test_functions)

def _generate_param_combinations(params: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Generate combinations of parameter values"""
    if not params:
        return [[]]

    result = []
    for value in params[0]['test_values']:
        for rest in _generate_param_combinations(params[1:]):
            result.append([{'name': params[0]['name'], 'value': value}] + rest)

    return result

def main():
    target = Path(sys.argv[1])
    mode = sys.argv[2]

    if target.is_file():
        files = [target]
    else:
        files = list(target.rglob('*.py'))

    total_tests = 0

    for file in files:
        try:
            # Skip test files
            if file.name.startswith('test_'):
                continue

            print(f"\n\033[33mGenerating tests for {file.relative_to(target)}\033[0m")

            # Parse and analyze source
            code = file.read_text()
            tree = ast.parse(code)

            # Generate test cases
            generator = TestGenerator()
            generator.visit(tree)

            if generator.test_cases:
                # Create test file
                test_file = file.parent / f'test_{file.name}'
                test_content = generate_test_file(file, generator.test_cases)

                if mode == 'generate':
                    test_file.write_text(test_content)
                    print(f"Generated {len(generator.test_cases)} test cases in {test_file.name}")
                else:
                    print("\nTest Preview:")
                    print(test_content)

                total_tests += len(generator.test_cases)
            else:
                print("No testable functions found")

        except Exception as e:
            print(f"\n\033[31mError processing {file}: {e}\033[0m")

    # Summary
    print(f"\n\033[34mSummary: Generated {total_tests} test cases\033[0m")
    if mode == 'generate':
        print("\nRun 'pytest' to execute the tests")

if __name__ == '__main__':
    main()
EOL "$target" "$mode"
}

# Register command
alias aitest='aiops_test'

# Command completion
compdef _aiops_commands aitest

# Update help
function aiops_help() {
    print -P "%F{blue}AI Operations Commands:%f"
    print -P "  airev     - Run AI code review"
    print -P "  aideps    - Analyze dependencies"
    print -P "  aiperf    - Analyze performance"
    print -P "  aidocs    - Analyze documentation"
    print -P "  airef     - Get refactoring suggestions"
    print -P "  aitest    - Generate test cases"
}
