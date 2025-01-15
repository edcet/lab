#!/usr/bin/env zsh

# AI Metrics System
# Development metrics collection and analysis

function aiops_metrics() {
    local action="$1"
    local target="${2:-.}"

    __ensure_aiops_components || return $?

    case "$action" in
        collect)
            print -P "%F{blue}Collecting Metrics%f"
            python3 - << 'EOL'
import sys
from pathlib import Path
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any
import git
import ast
import re

class MetricsCollector:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.metrics_dir = repo_path / '.ai' / 'metrics'
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def collect_all(self) -> Dict[str, Any]:
        """Collect all metrics"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'git': self.collect_git_metrics(),
            'code': self.collect_code_metrics(),
            'performance': self.collect_performance_metrics(),
            'quality': self.collect_quality_metrics()
        }

    def collect_git_metrics(self) -> Dict[str, Any]:
        """Collect git repository metrics"""
        try:
            repo = git.Repo(self.repo_path)

            # Commit activity
            commits = list(repo.iter_commits())
            today = datetime.now(timezone.utc).date()

            return {
                'total_commits': len(commits),
                'active_branches': len(list(repo.heads)),
                'contributors': len({c.author.email for c in commits}),
                'commits_today': sum(1 for c in commits if c.committed_datetime.date() == today),
                'commits_week': sum(1 for c in commits if (today - c.committed_datetime.date()).days <= 7),
                'lines_changed': {
                    'insertions': sum(c.stats.total['insertions'] for c in commits[:100]),
                    'deletions': sum(c.stats.total['deletions'] for c in commits[:100])
                }
            }
        except Exception as e:
            return {'error': str(e)}

    def collect_code_metrics(self) -> Dict[str, Any]:
        """Collect code metrics"""
        metrics = {
            'files': 0,
            'lines': 0,
            'functions': 0,
            'classes': 0,
            'comments': 0,
            'complexity': 0
        }

        try:
            for file in self.repo_path.rglob('*.py'):
                if 'test' not in file.name:
                    code = file.read_text()
                    tree = ast.parse(code)

                    metrics['files'] += 1
                    metrics['lines'] += len(code.splitlines())
                    metrics['functions'] += len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
                    metrics['classes'] += len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
                    metrics['comments'] += len([l for l in code.splitlines() if l.strip().startswith('#')])

                    # Calculate cyclomatic complexity
                    metrics['complexity'] += len([n for n in ast.walk(tree) if isinstance(n, (ast.If, ast.For, ast.While, ast.Try))])
        except Exception as e:
            return {'error': str(e)}

        return metrics

    def collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics"""
        try:
            import psutil
            process = psutil.Process()

            return {
                'memory': {
                    'rss': process.memory_info().rss / 1024 / 1024,  # MB
                    'vms': process.memory_info().vms / 1024 / 1024,  # MB
                    'percent': process.memory_percent()
                },
                'cpu': {
                    'percent': process.cpu_percent(interval=1.0),
                    'threads': process.num_threads()
                },
                'io': {
                    'read_bytes': process.io_counters().read_bytes / 1024 / 1024,  # MB
                    'write_bytes': process.io_counters().write_bytes / 1024 / 1024  # MB
                }
            }
        except Exception as e:
            return {'error': str(e)}

    def collect_quality_metrics(self) -> Dict[str, Any]:
        """Collect code quality metrics"""
        metrics = {
            'documentation': {
                'docstring_coverage': 0,
                'type_hint_coverage': 0
            },
            'testing': {
                'test_files': 0,
                'test_cases': 0,
                'coverage': 0
            },
            'style': {
                'pep8_violations': 0,
                'cognitive_complexity': 0
            }
        }

        try:
            total_functions = 0
            documented_functions = 0
            typed_functions = 0

            for file in self.repo_path.rglob('*.py'):
                if 'test' not in file.name:
                    code = file.read_text()
                    tree = ast.parse(code)

                    # Analyze functions
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            total_functions += 1
                            if ast.get_docstring(node):
                                documented_functions += 1
                            if node.returns or any(arg.annotation for arg in node.args.args):
                                typed_functions += 1

                    # Count test files and cases
                    test_file = file.parent / f'test_{file.name}'
                    if test_file.exists():
                        metrics['testing']['test_files'] += 1
                        test_code = test_file.read_text()
                        metrics['testing']['test_cases'] += len(re.findall(r'def test_', test_code))

            if total_functions > 0:
                metrics['documentation']['docstring_coverage'] = documented_functions / total_functions * 100
                metrics['documentation']['type_hint_coverage'] = typed_functions / total_functions * 100

        except Exception as e:
            return {'error': str(e)}

        return metrics

    def save_metrics(self, metrics: Dict[str, Any]):
        """Save metrics to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metrics_file = self.metrics_dir / f'metrics_{timestamp}.json'

        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        print(f"Metrics saved to {metrics_file}")

    def load_metrics_history(self) -> List[Dict[str, Any]]:
        """Load metrics history"""
        metrics_files = sorted(self.metrics_dir.glob('metrics_*.json'))

        history = []
        for file in metrics_files:
            with open(file) as f:
                history.append(json.load(f))

        return history

    def analyze_trends(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze metrics trends"""
        if not history:
            return {}

        trends = {}

        # Calculate changes
        latest = history[-1]
        previous = history[-2] if len(history) > 1 else None

        if previous:
            # Code growth
            trends['code_growth'] = {
                'files': latest['code']['files'] - previous['code']['files'],
                'lines': latest['code']['lines'] - previous['code']['lines']
            }

            # Quality trends
            trends['quality_trends'] = {
                'documentation': latest['quality']['documentation']['docstring_coverage'] - previous['quality']['documentation']['docstring_coverage'],
                'type_hints': latest['quality']['documentation']['type_hint_coverage'] - previous['quality']['documentation']['type_hint_coverage']
            }

            # Performance trends
            trends['performance_trends'] = {
                'memory': latest['performance']['memory']['percent'] - previous['performance']['memory']['percent'],
                'cpu': latest['performance']['cpu']['percent'] - previous['performance']['cpu']['percent']
            }

        return trends

def main():
    repo_path = Path(sys.argv[1])
    collector = MetricsCollector(repo_path)

    # Collect current metrics
    print("\033[34mCollecting metrics...\033[0m")
    metrics = collector.collect_all()
    collector.save_metrics(metrics)

    # Load history and analyze trends
    history = collector.load_metrics_history()
    trends = collector.analyze_trends(history)

    # Print summary
    print("\n\033[34mMetrics Summary:\033[0m")

    print("\nCode Metrics:")
    code_metrics = metrics['code']
    print(f"Files: {code_metrics['files']}")
    print(f"Lines: {code_metrics['lines']}")
    print(f"Functions: {code_metrics['functions']}")
    print(f"Classes: {code_metrics['classes']}")
    print(f"Complexity: {code_metrics['complexity']}")

    print("\nGit Metrics:")
    git_metrics = metrics['git']
    print(f"Total Commits: {git_metrics['total_commits']}")
    print(f"Active Branches: {git_metrics['active_branches']}")
    print(f"Contributors: {git_metrics['contributors']}")
    print(f"Commits Today: {git_metrics['commits_today']}")
    print(f"Commits This Week: {git_metrics['commits_week']}")

    print("\nQuality Metrics:")
    quality_metrics = metrics['quality']
    print(f"Docstring Coverage: {quality_metrics['documentation']['docstring_coverage']:.1f}%")
    print(f"Type Hint Coverage: {quality_metrics['documentation']['type_hint_coverage']:.1f}%")
    print(f"Test Files: {quality_metrics['testing']['test_files']}")
    print(f"Test Cases: {quality_metrics['testing']['test_cases']}")

    if trends:
        print("\n\033[34mTrends:\033[0m")
        code_growth = trends['code_growth']
        print(f"Files Change: {code_growth['files']:+d}")
        print(f"Lines Change: {code_growth['lines']:+d}")

        quality_trends = trends['quality_trends']
        print(f"Documentation Change: {quality_trends['documentation']:+.1f}%")
        print(f"Type Hints Change: {quality_trends['type_hints']:+.1f}%")

if __name__ == '__main__':
    main()
EOL "$target"
            ;;

        visualize)
            print -P "%F{blue}Visualizing Metrics%f"
            python3 - << 'EOL'
import sys
from pathlib import Path
import json
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import pandas as pd

def load_metrics_history(metrics_dir: Path) -> pd.DataFrame:
    """Load metrics history into a DataFrame"""
    data = []

    for file in sorted(metrics_dir.glob('metrics_*.json')):
        with open(file) as f:
            metrics = json.load(f)

        # Extract timestamp
        timestamp = datetime.fromisoformat(metrics['timestamp'])

        # Flatten metrics
        row = {
            'timestamp': timestamp,
            'files': metrics['code']['files'],
            'lines': metrics['code']['lines'],
            'functions': metrics['code']['functions'],
            'complexity': metrics['code']['complexity'],
            'docstring_coverage': metrics['quality']['documentation']['docstring_coverage'],
            'type_hint_coverage': metrics['quality']['documentation']['type_hint_coverage'],
            'test_cases': metrics['quality']['testing']['test_cases']
        }

        data.append(row)

    return pd.DataFrame(data)

def plot_metrics(df: pd.DataFrame):
    """Create visualization plots"""
    sns.set_style('whitegrid')

    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

    # Code size trends
    ax1.plot(df['timestamp'], df['files'], label='Files')
    ax1.plot(df['timestamp'], df['functions'], label='Functions')
    ax1.set_title('Code Size Trends')
    ax1.legend()
    ax1.tick_params(axis='x', rotation=45)

    # Code complexity
    ax2.plot(df['timestamp'], df['complexity'], color='red')
    ax2.set_title('Code Complexity Trend')
    ax2.tick_params(axis='x', rotation=45)

    # Documentation coverage
    ax3.plot(df['timestamp'], df['docstring_coverage'], label='Docstrings')
    ax3.plot(df['timestamp'], df['type_hint_coverage'], label='Type Hints')
    ax3.set_title('Documentation Coverage')
    ax3.legend()
    ax3.tick_params(axis='x', rotation=45)

    # Test coverage
    ax4.plot(df['timestamp'], df['test_cases'], color='green')
    ax4.set_title('Test Cases')
    ax4.tick_params(axis='x', rotation=45)

    plt.tight_layout()

    # Save plot
    plot_file = metrics_dir / 'metrics_visualization.png'
    plt.savefig(plot_file)
    print(f"\nVisualization saved to {plot_file}")

def main():
    repo_path = Path(sys.argv[1])
    metrics_dir = repo_path / '.ai' / 'metrics'

    if not metrics_dir.exists():
        print("\033[31mNo metrics data found. Run 'aiops metrics collect' first.\033[0m")
        return

    print("\033[34mGenerating visualizations...\033[0m")

    # Load and process data
    df = load_metrics_history(metrics_dir)

    if len(df) < 2:
        print("\033[33mNot enough data points for visualization. Collect more metrics over time.\033[0m")
        return

    # Create plots
    plot_metrics(df)

if __name__ == '__main__':
    main()
EOL "$target"
            ;;

        *)
            print -P "%F{red}Unknown action: $action%f"
            print -P "Try: collect, visualize"
            return 1
            ;;
    esac
}

# Register command
alias aimet='aiops_metrics'

# Command completion
compdef _aiops_commands aimet

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
}
