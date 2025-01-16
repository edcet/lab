"""NFX Neural CLI Commands

CLI commands for interacting with local LLM tools and autonomous operations.
"""

import click
import asyncio
import json
from typing import Optional
from .llm_interface import LLMInterface

@click.group()
def llm():
    """Local LLM tool commands"""
    pass

@llm.command()
@click.option('--task', '-t', required=True, help='Task description for autonomous execution')
@click.option('--system-prompt', '-s', help='Optional system prompt for LLMs')
def autonomous(task: str, system_prompt: Optional[str] = None):
    """Execute task autonomously using local LLMs"""
    async def run():
        interface = LLMInterface()

        # Initialize connections
        lm_studio_ready = await interface.init_lm_studio()
        ollama_ready = await interface.init_ollama()

        if not (lm_studio_ready or ollama_ready):
            click.echo("Error: No LLM tools available")
            return

        try:
            result = await interface.autonomous_task(task)

            # Display results
            click.echo("\n=== Task Analysis ===")
            click.echo(f"Agreement Level: {result['analysis']['agreement_level']:.2f}")

            click.echo("\n=== Confidence Scores ===")
            for model, score in result['analysis']['confidence_scores'].items():
                click.echo(f"{model}: {score:.2f}")

            click.echo("\n=== Unique Suggestions ===")
            for i, suggestion in enumerate(result['analysis']['unique_suggestions'], 1):
                click.echo(f"{i}. {suggestion}")

            click.echo("\n=== Suggested Actions ===")
            for i, action in enumerate(result['suggested_actions'], 1):
                click.echo(f"{i}. [{action['priority']}] {action['description']}")
                click.echo(f"   Source: {action['source_model']}")

        except Exception as e:
            click.echo(f"Error executing task: {e}")
        finally:
            await interface.cleanup()

    asyncio.run(run())

@llm.command()
@click.option('--prompt', '-p', required=True, help='Prompt to send to LLMs')
@click.option('--system-prompt', '-s', help='Optional system prompt for LLMs')
def query(prompt: str, system_prompt: Optional[str] = None):
    """Query both LM Studio and Ollama in parallel"""
    async def run():
        interface = LLMInterface()

        # Initialize connections
        lm_studio_ready = await interface.init_lm_studio()
        ollama_ready = await interface.init_ollama()

        if not (lm_studio_ready or ollama_ready):
            click.echo("Error: No LLM tools available")
            return

        try:
            responses = await interface.parallel_query(prompt, system_prompt)

            for response in responses:
                click.echo(f"\n=== {response.model} Response ===")
                click.echo(response.text)
                click.echo(f"\nTimestamp: {response.timestamp}")

        except Exception as e:
            click.echo(f"Error querying LLMs: {e}")
        finally:
            await interface.cleanup()

    asyncio.run(run())

@llm.command()
def status():
    """Check status of LLM tools"""
    async def run():
        interface = LLMInterface()

        click.echo("Checking LLM tool status...")

        # Check LM Studio
        lm_studio_ready = await interface.init_lm_studio()
        click.echo(f"LM Studio: {'READY' if lm_studio_ready else 'NOT AVAILABLE'}")

        # Check Ollama
        ollama_ready = await interface.init_ollama()
        click.echo(f"Ollama: {'READY' if ollama_ready else 'NOT AVAILABLE'}")

        await interface.cleanup()

    asyncio.run(run())
