"""Documentation System for Core Components"""

import asyncio
import inspect
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import ast
import docstring_parser
import markdown
import yaml

@dataclass
class DocConfig:
    """Documentation configuration"""
    output_dir: str = "docs"
    template_dir: str = "templates"
    format: str = "markdown"
    include_private: bool = False
    include_source: bool = True
    version_tracking: bool = True

@dataclass
class ComponentDoc:
    """Component documentation"""
    name: str
    description: str
    version: str
    author: str
    created_at: datetime
    updated_at: datetime
    dependencies: List[str]
    methods: List[Dict[str, Any]]
    examples: List[Dict[str, Any]]
    source_file: str

class DocumentationSystem:
    """Core documentation system"""

    def __init__(self, config_path: str = "~/.config/docs"):
        self.config_path = Path(config_path).expanduser()
        self.config_path.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.config = self._load_config()

        # Initialize paths
        self.output_dir = Path(self.config.output_dir).expanduser()
        self.template_dir = Path(self.config.template_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Component registry
        self.components: Dict[str, ComponentDoc] = {}

        # Version tracking
        self.versions: Dict[str, List[str]] = {}

        # Template cache
        self.templates: Dict[str, str] = {}

    def _load_config(self) -> DocConfig:
        """Load documentation configuration"""
        config_file = self.config_path / "config.yaml"

        if config_file.exists():
            with open(config_file) as f:
                config_data = yaml.safe_load(f)
                return DocConfig(**config_data)

        # Default configuration
        return DocConfig()

    async def generate_docs(self, source_dir: str):
        """Generate documentation for all components in source directory"""
        source_path = Path(source_dir).expanduser()

        # Find all Python files
        python_files = list(source_path.rglob("*.py"))

        # Process files in parallel
        tasks = [
            self._process_file(file)
            for file in python_files
        ]
        await asyncio.gather(*tasks)

        # Generate index
        await self._generate_index()

        # Track versions if enabled
        if self.config.version_tracking:
            await self._track_versions()

    async def _process_file(self, file_path: Path):
        """Process a single Python file"""
        try:
            # Parse file
            with open(file_path) as f:
                tree = ast.parse(f.read())

            # Extract module info
            module_doc = ast.get_docstring(tree)
            if not module_doc:
                return

            # Parse classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    await self._process_class(node, file_path)
                elif isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_') or self.config.include_private:
                        await self._process_function(node, file_path)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    async def _process_class(self, node: ast.ClassDef, file_path: Path):
        """Process a class definition"""
        # Parse class docstring
        class_doc = ast.get_docstring(node)
        if not class_doc:
            return

        parsed_doc = docstring_parser.parse(class_doc)

        # Extract methods
        methods = []
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                if not child.name.startswith('_') or self.config.include_private:
                    method_doc = await self._extract_method_info(child)
                    if method_doc:
                        methods.append(method_doc)

        # Create component documentation
        component = ComponentDoc(
            name=node.name,
            description=parsed_doc.short_description or "",
            version=self._extract_version(parsed_doc),
            author=self._extract_author(parsed_doc),
            created_at=datetime.now(),  # Could be extracted from git history
            updated_at=datetime.now(),
            dependencies=self._extract_dependencies(parsed_doc),
            methods=methods,
            examples=self._extract_examples(parsed_doc),
            source_file=str(file_path)
        )

        # Store component documentation
        self.components[node.name] = component

        # Generate component documentation
        await self._generate_component_doc(component)

    async def _extract_method_info(self, node: ast.FunctionDef) -> Optional[Dict[str, Any]]:
        """Extract documentation info from a method"""
        method_doc = ast.get_docstring(node)
        if not method_doc:
            return None

        parsed_doc = docstring_parser.parse(method_doc)

        return {
            "name": node.name,
            "description": parsed_doc.short_description or "",
            "long_description": parsed_doc.long_description or "",
            "parameters": [
                {
                    "name": param.arg_name,
                    "type": param.type_name,
                    "description": param.description
                }
                for param in parsed_doc.params
            ],
            "returns": {
                "type": parsed_doc.returns.type_name if parsed_doc.returns else None,
                "description": parsed_doc.returns.description if parsed_doc.returns else None
            },
            "examples": [
                example.description
                for example in parsed_doc.examples
            ],
            "source": self._get_source(node) if self.config.include_source else None
        }

    def _extract_version(self, doc) -> str:
        """Extract version from docstring"""
        for meta in doc.meta:
            if meta.args.lower() == "version":
                return meta.description
        return "0.1.0"  # Default version

    def _extract_author(self, doc) -> str:
        """Extract author from docstring"""
        for meta in doc.meta:
            if meta.args.lower() == "author":
                return meta.description
        return "Unknown"  # Default author

    def _extract_dependencies(self, doc) -> List[str]:
        """Extract dependencies from docstring"""
        for meta in doc.meta:
            if meta.args.lower() == "dependencies":
                return [dep.strip() for dep in meta.description.split(",")]
        return []

    def _extract_examples(self, doc) -> List[Dict[str, Any]]:
        """Extract examples from docstring"""
        examples = []
        for example in doc.examples:
            examples.append({
                "description": example.description,
                "code": example.snippet
            })
        return examples

    def _get_source(self, node: ast.AST) -> str:
        """Get source code for a node"""
        return ast.unparse(node)

    async def _generate_component_doc(self, component: ComponentDoc):
        """Generate documentation for a component"""
        # Load template
        template = await self._load_template("component")

        # Generate documentation
        doc_content = template.format(
            name=component.name,
            description=component.description,
            version=component.version,
            author=component.author,
            created_at=component.created_at.isoformat(),
            updated_at=component.updated_at.isoformat(),
            dependencies=", ".join(component.dependencies),
            methods=self._format_methods(component.methods),
            examples=self._format_examples(component.examples)
        )

        # Save documentation
        doc_path = self.output_dir / f"{component.name.lower()}.md"
        with open(doc_path, "w") as f:
            f.write(doc_content)

    async def _load_template(self, template_name: str) -> str:
        """Load a documentation template"""
        if template_name in self.templates:
            return self.templates[template_name]

        template_path = self.template_dir / f"{template_name}.md"
        if not template_path.exists():
            # Use default template
            return self._get_default_template(template_name)

        with open(template_path) as f:
            template = f.read()
            self.templates[template_name] = template
            return template

    def _get_default_template(self, template_name: str) -> str:
        """Get default template content"""
        if template_name == "component":
            return """# {name}

{description}

## Version
{version}

## Author
{author}

## Created
{created_at}

## Last Updated
{updated_at}

## Dependencies
{dependencies}

## Methods
{methods}

## Examples
{examples}
"""

        elif template_name == "index":
            return """# API Documentation

{components}
"""

        return ""

    def _format_methods(self, methods: List[Dict[str, Any]]) -> str:
        """Format methods documentation"""
        formatted = []
        for method in methods:
            formatted.append(f"### {method['name']}\n")
            formatted.append(f"{method['description']}\n")

            if method['long_description']:
                formatted.append(f"{method['long_description']}\n")

            if method['parameters']:
                formatted.append("\nParameters:\n")
                for param in method['parameters']:
                    formatted.append(
                        f"- `{param['name']}` ({param['type']}): {param['description']}\n"
                    )

            if method['returns']['type']:
                formatted.append(
                    f"\nReturns:\n{method['returns']['type']}: {method['returns']['description']}\n"
                )

            if method['examples']:
                formatted.append("\nExamples:\n")
                for example in method['examples']:
                    formatted.append(f"```python\n{example}\n```\n")

            if method['source']:
                formatted.append(f"\nSource:\n```python\n{method['source']}\n```\n")

        return "\n".join(formatted)

    def _format_examples(self, examples: List[Dict[str, Any]]) -> str:
        """Format examples documentation"""
        formatted = []
        for example in examples:
            formatted.append(f"### {example['description']}\n")
            formatted.append(f"```python\n{example['code']}\n```\n")
        return "\n".join(formatted)

    async def _generate_index(self):
        """Generate documentation index"""
        # Load template
        template = await self._load_template("index")

        # Generate component list
        components = []
        for name, component in sorted(self.components.items()):
            components.append(
                f"- [{name}]({name.lower()}.md): {component.description}"
            )

        # Generate index
        index_content = template.format(
            components="\n".join(components)
        )

        # Save index
        index_path = self.output_dir / "index.md"
        with open(index_path, "w") as f:
            f.write(index_content)

    async def _track_versions(self):
        """Track documentation versions"""
        version_dir = self.output_dir / "versions"
        version_dir.mkdir(exist_ok=True)

        # Create version snapshot
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_path = version_dir / version
        version_path.mkdir()

        # Copy current docs to version directory
        for doc_file in self.output_dir.glob("*.md"):
            if doc_file.name != "versions":
                with open(doc_file) as f:
                    content = f.read()

                with open(version_path / doc_file.name, "w") as f:
                    f.write(content)

        # Update version tracking
        for component in self.components:
            if component not in self.versions:
                self.versions[component] = []
            self.versions[component].append(version)

        # Save version info
        version_info = {
            "timestamp": datetime.now().isoformat(),
            "components": {
                component: versions
                for component, versions in self.versions.items()
            }
        }

        with open(version_dir / "versions.json", "w") as f:
            json.dump(version_info, f, indent=2)

    async def build_html(self):
        """Build HTML documentation from markdown"""
        html_dir = self.output_dir / "html"
        html_dir.mkdir(exist_ok=True)

        # Process all markdown files
        for md_file in self.output_dir.glob("*.md"):
            if md_file.name != "versions":
                # Read markdown
                with open(md_file) as f:
                    md_content = f.read()

                # Convert to HTML
                html_content = markdown.markdown(
                    md_content,
                    extensions=['fenced_code', 'tables']
                )

                # Save HTML
                html_path = html_dir / f"{md_file.stem}.html"
                with open(html_path, "w") as f:
                    f.write(html_content)

    async def search_docs(self, query: str) -> List[Dict[str, Any]]:
        """Search documentation"""
        results = []

        for component in self.components.values():
            # Search in component description
            if query.lower() in component.description.lower():
                results.append({
                    "type": "component",
                    "name": component.name,
                    "match": "description",
                    "content": component.description
                })

            # Search in methods
            for method in component.methods:
                if query.lower() in method["description"].lower():
                    results.append({
                        "type": "method",
                        "component": component.name,
                        "name": method["name"],
                        "match": "description",
                        "content": method["description"]
                    })

                # Search in examples
                for example in method["examples"]:
                    if query.lower() in example.lower():
                        results.append({
                            "type": "example",
                            "component": component.name,
                            "method": method["name"],
                            "content": example
                        })

        return results

    async def get_component_versions(self, component_name: str) -> List[Dict[str, Any]]:
        """Get version history for a component"""
        if not self.config.version_tracking:
            return []

        if component_name not in self.versions:
            return []

        versions = []
        version_dir = self.output_dir / "versions"

        for version in self.versions[component_name]:
            version_path = version_dir / version / f"{component_name.lower()}.md"
            if version_path.exists():
                with open(version_path) as f:
                    content = f.read()

                versions.append({
                    "version": version,
                    "timestamp": datetime.strptime(
                        version, "%Y%m%d_%H%M%S"
                    ).isoformat(),
                    "content": content
                })

        return sorted(versions, key=lambda v: v["version"], reverse=True)

    async def cleanup_old_versions(self, keep_days: int = 30):
        """Clean up old documentation versions"""
        if not self.config.version_tracking:
            return

        version_dir = self.output_dir / "versions"
        if not version_dir.exists():
            return

        cutoff = datetime.now().timestamp() - (keep_days * 86400)

        for version_path in version_dir.iterdir():
            if version_path.is_dir():
                try:
                    version_time = datetime.strptime(
                        version_path.name, "%Y%m%d_%H%M%S"
                    ).timestamp()

                    if version_time < cutoff:
                        # Remove old version
                        for file in version_path.iterdir():
                            file.unlink()
                        version_path.rmdir()
                except ValueError:
                    continue  # Skip if directory name doesn't match version format
