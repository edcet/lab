#!/usr/bin/env python3
"""🌟 Digital Wizard's Companion - Your Homelab, Your Magic 🌟"""

import asyncio
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from pathlib import Path
import random

class DigitalWizard:
    """Your personal magical companion"""

    def __init__(self):
        self.console = Console()
        self.layout = self._create_sanctum()
        # Import personalities from ModelMagic
        self.personalities = MODEL_PERSONALITIES  # From model_magic.py lines 22-47
        self.current_mood = random.choice(["playful", "mysterious", "philosophical"])

        # Track user's growing power
        self.user_achievements = {
            "spells_cast": 0,
            "systems_enchanted": 0,
            "wisdom_gained": 0
        }

        # Initialize magical components with user empowerment focus
        self.crystal = PerformanceCrystal()  # From performance_crystal.py
        self.store = RadicalStore(
            db_path=Path("~/.wizard/grimoire.db").expanduser(),
            evolution_config={"learning_rate": "adaptive"}
        )

    async def awaken(self):
        """Begin the magical journey"""
        with Live(self.layout, refresh_per_second=4) as live:
            await self._reveal_sanctum()
            while True:
                intention = await self._sense_intention()
                if intention.type == "exploration":
                    await self._guide_exploration(intention)
                elif intention.type == "creation":
                    await self._empower_creation(intention)
                elif intention.type == "mastery":
                    await self._share_wisdom(intention)

                # Evolve with the user
                await self._evolve_together(intention)

    async def _sense_intention(self):
        """Understand the user's true intention"""
        prompt = self._create_magical_prompt()
        response = await self.console.input(prompt)

        # Use pattern matching from build_self.py (lines 111-125)
        patterns = await self.store.get_matching_patterns(response)

        return IntentionPattern(
            raw_input=response,
            patterns=patterns,
            energy=self._measure_magical_energy(response)
        )

    async def _empower_creation(self, intention):
        """Help users create their own magic"""
        self.console.print(Panel(
            f"[bold cyan]The power flows through you...[/bold cyan]\n\n"
            f"[green]What would you like to create today?[/green]\n"
            f"1. 🌟 New Enchantment (Custom Script)\n"
            f"2. 🔮 Magical Integration (Service Connection)\n"
            f"3. ⚡️ Power Ritual (Resource Optimization)\n"
            f"4. 📚 Wisdom Codex (Documentation)",
            title="[bold]Creator's Sanctum[/bold]"
        ))

        choice = await self.console.input("[cyan]Your creative vision: [/cyan]")

        # Use the RadicalStore to learn from user's creative patterns
        await self._capture_creative_pattern(choice, intention)

        # Empower the user with feedback
        self.console.print(f"\n[bold green]✨ Your magic grows stronger! ✨[/bold green]")
        self.user_achievements["wisdom_gained"] += 1

    def _create_magical_prompt(self):
        """Create a context-aware magical prompt"""
        # Use harmony score from performance_crystal.py (lines 82-96)
        harmony = self.crystal.harmony_score

        if harmony > 90:
            return "✨ Your sanctum hums with power. What shall we create? "
        elif harmony > 70:
            return "🌟 The magical energies are balanced. How may I assist? "
        else:
            return "⚡️ The system seeks harmony. What needs attention? "

    async def _evolve_together(self, intention):
        """Grow and evolve with the user"""
        # Use evolution tracking from build_self.py (lines 161-179)
        evolution_data = await self.store.track_evolution({
            "intention": intention,
            "achievements": self.user_achievements,
            "harmony": self.crystal.harmony_score
        })

        # Unlock new capabilities based on user growth
        if evolution_data.indicates_growth:
            await self._reveal_new_power(evolution_data)
