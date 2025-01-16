#!/usr/bin/env python3
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import aiohttp
import rich.progress
from rich.console import Console
from rich.logging import RichHandler
import yaml
import difflib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("analyzer")
console = Console()

class OllamaInterface:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.models = {"codellama": None, "qwq": None}

    async def generate(self, model: str, prompt: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt}
            ) as resp:
                response = await resp.json()
                return response.get("response", "")

    async def analyze_code(self, code: str) -> Dict[str, Any]:
        prompt = f"Analyze this code and provide insights:\n{code}"
        analysis = await self.generate("codellama", prompt)
        return {"analysis": analysis}

    async def reason_about_integration(self, context: str) -> Dict[str, Any]:
        prompt = f"Reason about system integration given this context:\n{context}"
        reasoning = await self.generate("qwq", prompt)
        return {"reasoning": reasoning}

class DocumentAnalyzer:
    def __init__(self, docs_path: Path, codebase_path: Path):
        self.docs_path = docs_path
        self.codebase_path = codebase_path

    async def analyze_documentation(self) -> Dict[str, Any]:
        docs_files = list(self.docs_path.glob("**/*.md"))
        analysis_results = {}
        
        with rich.progress.Progress() as progress:
            task = progress.add_task("[cyan]Analyzing documentation...", total=len(docs_files))
            
            for doc_file in docs_files:
                relative_path = doc_file.relative_to(self.docs_path)
                with doc_file.open() as f:
                    content = f.read()
                    
                # Compare with actual implementation
                code_refs = self.extract_code_references(content)
                implementation_gaps = await self.verify_implementation(code_refs)
                
                analysis_results[str(relative_path)] = {
                    "content": content,
                    "implementation_gaps": implementation_gaps
                }
                
                progress.update(task, advance=1)
            
        return analysis_results

    def extract_code_references(self, content: str) -> List[str]:
        # Extract code paths and references from documentation
        # This is a simplified implementation
        return []

    async def verify_implementation(self, code_refs: List[str]) -> List[str]:
        # Verify each code reference against actual implementation
        return []

class DeploymentPlanner:
    def __init__(self, ollama: OllamaInterface):
        self.ollama = ollama

    async def generate_deployment_plan(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        context = yaml.dump(analysis_results)
        
        integration_plan = await self.ollama.reason_about_integration(
            f"Generate deployment plan for AutoGPT, Ollama, and Jan based on analysis:\n{context}"
        )
        
        return {
            "deployment_plan": integration_plan,
            "components": {
                "autogpt": {"status": "planned", "dependencies": ["ollama"]},
                "ollama": {"status": "planned", "dependencies": []},
                "jan": {"status": "planned", "dependencies": ["ollama"]}
            }
        }

class ArchivalManager:
    def __init__(self, docs_path: Path):
        self.docs_path = docs_path
        self.archive_path = docs_path / "archive"

    async def archive_outdated_docs(self, analysis_results: Dict[str, Any]):
        self.archive_path.mkdir(exist_ok=True)
        
        with rich.progress.Progress() as progress:
            task = progress.add_task("[yellow]Archiving outdated documentation...", total=len(analysis_results))
            
            for doc_path, analysis in analysis_results.items():
                if analysis.get("implementation_gaps"):
                    source = self.docs_path / doc_path
                    target = self.archive_path / f"{doc_path}.archived"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    
                    if source.exists():
                        source.rename(target)
                    
                progress.update(task, advance=1)

async def main():
    try:
        ollama = OllamaInterface()
        docs_path = Path("docs")
        codebase_path = Path(".")
        
        # Initialize components
        doc_analyzer = DocumentAnalyzer(docs_path, codebase_path)
        deployment_planner = DeploymentPlanner(ollama)
        archival_manager = ArchivalManager(docs_path)
        
        # Execute analysis pipeline
        with console.status("[bold green]Executing analysis pipeline..."):
            analysis_results = await doc_analyzer.analyze_documentation()
            deployment_plan = await deployment_planner.generate_deployment_plan(analysis_results)
            await archival_manager.archive_outdated_docs(analysis_results)
        
        # Generate reports
        output_path = Path("analysis_results")
        output_path.mkdir(exist_ok=True)
        
        with open(output_path / "analysis.yaml", "w") as f:
            yaml.dump(analysis_results, f)
        
        with open(output_path / "deployment_plan.yaml", "w") as f:
            yaml.dump(deployment_plan, f)
        
        console.print("[bold green]Analysis complete! Results saved to analysis_results/")
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

