#!/usr/bin/env zsh

# AI Security System
# Security analysis and enhancement

function aiops_security() {
    local action="$1"
    local target="${2:-.}"

    __ensure_aiops_components || return $?

    case "$action" in
        scan)
            print -P "%F{blue}Security Scan%f"
            python3 - << 'EOL'
import sys
from pathlib import Path
import ast
import re
from typing import Dict, List, Any
from dataclasses import dataclass
import json
import subprocess

@dataclass
class SecurityIssue:
    severity: str
    category: str
    description: str
    file: str
    line: int
    snippet: str
    recommendation: str

class SecurityScanner:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.issues: List[SecurityIssue] = []
        self.security_patterns = {
            'sql_injection': [
                r'execute\s*\(\s*[\'"][^\']*%|cursor\.execute\s*\(\s*[\'"][^\']*%',
                r'raw_input\s*\(\s*\)|input\s*\(\s*\)',
            ],
            'command_injection': [
                r'os\.system\s*\(\s*[\'"][^\']*\$|subprocess\.call\s*\(\s*[\'"][^\']*\$',
                r'eval\s*\(\s*|exec\s*\(\s*',
            ],
            'path_traversal': [
                r'open\s*\(\s*[\'"][^\']*\.\.',
                r'file_get_contents\s*\(\s*[\'"][^\']*\.\.',
            ],
            'hardcoded_secrets': [
                r'password\s*=\s*[\'"][^\'"]{8,}[\'"]',
                r'api_key\s*=\s*[\'"][^\'"]{8,}[\'"]',
                r'secret\s*=\s*[\'"][^\'"]{8,}[\'"]',
            ],
            'insecure_hash': [
                r'md5\s*\(\s*|sha1\s*\(\s*',
            ],
            'debug_code': [
                r'print\s*\(\s*[\'"]debug|console\.log\s*\(\s*[\'"]debug',
                r'debugger|alert\s*\(\s*',
            ]
        }

    def scan_file(self, file_path: Path) -> List[SecurityIssue]:
        """Scan a single file for security issues"""
        try:
            code = file_path.read_text()
            lines = code.splitlines()
            issues = []

            # Pattern-based scanning
            for category, patterns in self.security_patterns.items():
                for pattern in patterns:
                    for match in re.finditer(pattern, code):
                        line_no = code.count('\n', 0, match.start()) + 1
                        line = lines[line_no - 1].strip()
                        issues.append(SecurityIssue(
                            severity='high',
                            category=category,
                            description=f'Potential {category.replace("_", " ")} vulnerability',
                            file=str(file_path),
                            line=line_no,
                            snippet=line,
                            recommendation=self._get_recommendation(category)
                        ))

            # AST-based scanning
            tree = ast.parse(code)
            visitor = SecurityVisitor(file_path, lines)
            visitor.visit(tree)
            issues.extend(visitor.issues)

            return issues
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
            return []

    def _get_recommendation(self, category: str) -> str:
        """Get security recommendation for a category"""
        recommendations = {
            'sql_injection': 'Use parameterized queries or an ORM',
            'command_injection': 'Use subprocess.run with shell=False and input validation',
            'path_traversal': 'Use os.path.abspath and validate file paths',
            'hardcoded_secrets': 'Use environment variables or a secure secret management system',
            'insecure_hash': 'Use strong hashing algorithms like bcrypt or Argon2',
            'debug_code': 'Remove debug code before deployment'
        }
        return recommendations.get(category, 'Review and fix the security issue')

    def scan_dependencies(self) -> List[SecurityIssue]:
        """Scan dependencies for known vulnerabilities"""
        issues = []
        try:
            # Run safety check
            result = subprocess.run(
                ['safety', 'check', '--json'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                vulns = json.loads(result.stdout)
                for vuln in vulns:
                    issues.append(SecurityIssue(
                        severity='high',
                        category='vulnerable_dependency',
                        description=f'Vulnerable package: {vuln["package"]} {vuln["installed_version"]}',
                        file='requirements.txt',
                        line=0,
                        snippet=f'{vuln["package"]}=={vuln["installed_version"]}',
                        recommendation=f'Upgrade to version {vuln["fixed_version"]} or later'
                    ))
        except Exception as e:
            print(f"Error scanning dependencies: {e}")
        return issues

    def scan_git_secrets(self) -> List[SecurityIssue]:
        """Scan git history for secrets"""
        issues = []
        try:
            # Run gitleaks
            result = subprocess.run(
                ['gitleaks', 'detect', '--no-git', '--format=json'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout:
                leaks = json.loads(result.stdout)
                for leak in leaks:
                    issues.append(SecurityIssue(
                        severity='critical',
                        category='exposed_secret',
                        description=f'Secret found in git history: {leak["rule"]}',
                        file=leak["file"],
                        line=leak["line"],
                        snippet=leak["match"],
                        recommendation='Remove secret and rotate credentials'
                    ))
        except Exception as e:
            print(f"Error scanning git history: {e}")
        return issues

class SecurityVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, lines: List[str]):
        self.file_path = file_path
        self.lines = lines
        self.issues: List[SecurityIssue] = []

    def visit_Call(self, node):
        """Check function calls for security issues"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            line_no = node.lineno
            line = self.lines[line_no - 1].strip()

            # Check for dangerous functions
            dangerous_funcs = {
                'eval': 'Code injection risk',
                'exec': 'Code injection risk',
                'pickle.loads': 'Deserialization vulnerability',
                'yaml.load': 'YAML deserialization vulnerability'
            }

            if func_name in dangerous_funcs:
                self.issues.append(SecurityIssue(
                    severity='high',
                    category='dangerous_function',
                    description=dangerous_funcs[func_name],
                    file=str(self.file_path),
                    line=line_no,
                    snippet=line,
                    recommendation=f'Avoid using {func_name} with untrusted input'
                ))

        self.generic_visit(node)

    def visit_Import(self, node):
        """Check imports for security issues"""
        dangerous_imports = {
            'telnetlib': 'Insecure protocol',
            'ftplib': 'Insecure protocol',
            'pickle': 'Unsafe serialization'
        }

        for name in node.names:
            if name.name in dangerous_imports:
                self.issues.append(SecurityIssue(
                    severity='medium',
                    category='dangerous_import',
                    description=f'Using {dangerous_imports[name.name]}',
                    file=str(self.file_path),
                    line=node.lineno,
                    snippet=self.lines[node.lineno - 1].strip(),
                    recommendation=f'Use a secure alternative to {name.name}'
                ))

        self.generic_visit(node)

def main():
    repo_path = Path(sys.argv[1])
    scanner = SecurityScanner(repo_path)
    all_issues = []

    print("\033[34mScanning for security issues...\033[0m")

    # Scan Python files
    for file in repo_path.rglob('*.py'):
        print(f"\nScanning {file.relative_to(repo_path)}")
        issues = scanner.scan_file(file)
        if issues:
            all_issues.extend(issues)
            print(f"Found {len(issues)} potential issues")
        else:
            print("✓ No issues found")

    # Scan dependencies
    print("\n\033[34mScanning dependencies...\033[0m")
    dep_issues = scanner.scan_dependencies()
    if dep_issues:
        all_issues.extend(dep_issues)
        print(f"Found {len(dep_issues)} vulnerable dependencies")

    # Scan git history
    print("\n\033[34mScanning git history...\033[0m")
    git_issues = scanner.scan_git_secrets()
    if git_issues:
        all_issues.extend(git_issues)
        print(f"Found {len(git_issues)} potential secrets")

    # Generate report
    if all_issues:
        print("\n\033[34mSecurity Issues:\033[0m")
        by_severity = {'critical': [], 'high': [], 'medium': [], 'low': []}
        for issue in all_issues:
            by_severity[issue.severity].append(issue)

        for severity in ['critical', 'high', 'medium', 'low']:
            issues = by_severity[severity]
            if issues:
                print(f"\n{severity.upper()} Severity Issues:")
                for issue in issues:
                    print(f"\n[{issue.category}] {issue.file}:{issue.line}")
                    print(f"Description: {issue.description}")
                    print(f"Code: {issue.snippet}")
                    print(f"Recommendation: {issue.recommendation}")

        # Save detailed report
        report_file = repo_path / '.ai' / 'security_report.json'
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump([vars(issue) for issue in all_issues], f, indent=2)
        print(f"\nDetailed report saved to {report_file}")
    else:
        print("\n✓ No security issues found")

if __name__ == '__main__':
    main()
EOL "$target"
            ;;

        fix)
            print -P "%F{blue}Fixing Security Issues%f"
            python3 - << 'EOL'
import sys
from pathlib import Path
import json
from typing import Dict, Any, List
import re

def load_security_report(repo_path: Path) -> List[Dict[str, Any]]:
    """Load security report"""
    report_file = repo_path / '.ai' / 'security_report.json'
    if not report_file.exists():
        print("\033[31mNo security report found. Run 'aiops security scan' first.\033[0m")
        return []

    with open(report_file) as f:
        return json.load(f)

def fix_security_issues(repo_path: Path, issues: List[Dict[str, Any]]) -> None:
    """Fix security issues"""
    fixes_by_file: Dict[str, List[Dict[str, Any]]] = {}

    # Group fixes by file
    for issue in issues:
        if issue['file'] not in fixes_by_file:
            fixes_by_file[issue['file']] = []
        fixes_by_file[issue['file']].append(issue)

    # Apply fixes
    for file_path, file_issues in fixes_by_file.items():
        try:
            with open(file_path) as f:
                content = f.read()
                lines = content.splitlines()

            # Sort issues by line number in reverse order
            file_issues.sort(key=lambda x: x['line'], reverse=True)

            # Apply fixes from bottom to top
            for issue in file_issues:
                fix = generate_fix(issue)
                if fix:
                    line_index = issue['line'] - 1
                    lines[line_index] = fix

            # Write fixed content
            with open(file_path, 'w') as f:
                f.write('\n'.join(lines))

            print(f"\nFixed issues in {file_path}")
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")

def generate_fix(issue: Dict[str, Any]) -> str:
    """Generate fix for a security issue"""
    category = issue['category']
    line = issue['snippet']

    if category == 'sql_injection':
        # Convert to parameterized query
        if 'execute' in line:
            return line.replace('%s', '?').replace('%d', '?')

    elif category == 'command_injection':
        # Convert to safer subprocess call
        if 'os.system' in line:
            cmd = re.search(r'os\.system\s*\(\s*[\'"]([^\'"]+)[\'"]', line)
            if cmd:
                return f"subprocess.run([{', '.join(repr(arg) for arg in cmd.group(1).split())}], shell=False)"

    elif category == 'hardcoded_secrets':
        # Convert to environment variable
        secret_name = re.search(r'(\w+)\s*=\s*[\'"][^\'"]+[\'"]', line)
        if secret_name:
            return f"{secret_name.group(1)} = os.environ.get('{secret_name.group(1).upper()}')"

    elif category == 'insecure_hash':
        # Convert to secure hash
        if 'md5' in line or 'sha1' in line:
            return line.replace('md5', 'hashlib.sha256').replace('sha1', 'hashlib.sha256')

    elif category == 'debug_code':
        # Comment out debug code
        return f"# {line}  # TODO: Remove debug code"

    return ""

def main():
    repo_path = Path(sys.argv[1])
    issues = load_security_report(repo_path)

    if not issues:
        return

    print("\033[34mFixing security issues...\033[0m")
    fix_security_issues(repo_path, issues)

    print("\n✓ Security fixes applied")
    print("Please review the changes and test thoroughly")

if __name__ == '__main__':
    main()
EOL "$target"
            ;;

        *)
            print -P "%F{red}Unknown action: $action%f"
            print -P "Try: scan, fix"
            return 1
            ;;
    esac
}

# Register command
alias aisec='aiops_security'

# Command completion
compdef _aiops_commands aisec

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
    print -P "  aisec     - Analyze and fix security issues"
}
