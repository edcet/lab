"""NFX Setup Module

Advanced AI setup for NFX with integrated AutoGPT functionality.
Includes AI profile configuration, directives management, and neural setup.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from rich.console import Console
from rich.prompt import Confirm, Prompt

from nfx.core.config import NFXConfig
from nfx.core.utils.input import InputHandler
from nfx.core.utils.telemetry import telemetry_manager

logger = logging.getLogger(__name__)
console = Console()
input_handler = InputHandler()

class AIRole(str, Enum):
    """Available AI roles"""
    ASSISTANT = "assistant"  # General purpose assistant
    SPECIALIST = "specialist"  # Domain specialist
    RESEARCHER = "researcher"  # Research and analysis
    ENGINEER = "engineer"  # Technical implementation
    ARCHITECT = "architect"  # System design
    WARRIOR = "warrior"  # Neural warfare

@dataclass
class AIProfile:
    """AI profile configuration"""
    name: str
    role: AIRole
    description: str
    capabilities: Set[str] = field(default_factory=set)
    specializations: Set[str] = field(default_factory=set)
    neural_patterns: Set[str] = field(default_factory=set)
    quantum_states: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

@dataclass
class AIDirectives:
    """AI operational directives"""
    resources: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    neural_protocols: List[str] = field(default_factory=list)
    quantum_protocols: List[str] = field(default_factory=list)
    warfare_protocols: List[str] = field(default_factory=list)

class SetupManager:
    """Manages AI setup and configuration"""

    def __init__(
        self,
        config: NFXConfig,
        profile_dir: Optional[Path] = None,
        allow_warfare: bool = False
    ):
        """Initialize setup manager

        Args:
            config: NFX configuration
            profile_dir: Optional profile directory
            allow_warfare: Allow warfare capabilities
        """
        self.config = config
        self.profile_dir = profile_dir or Path.home() / ".nfx" / "profiles"
        self.allow_warfare = allow_warfare
        self._setup_profile_dir()

    def _setup_profile_dir(self) -> None:
        """Setup profile directory"""
        if self.profile_dir:
            self.profile_dir.mkdir(parents=True, exist_ok=True)

    async def apply_overrides(
        self,
        profile: AIProfile,
        directives: AIDirectives,
        override_name: Optional[str] = None,
        override_role: Optional[AIRole] = None,
        replace_directives: bool = False,
        resources: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        best_practices: Optional[List[str]] = None,
        neural_protocols: Optional[List[str]] = None,
        quantum_protocols: Optional[List[str]] = None,
        warfare_protocols: Optional[List[str]] = None
    ) -> None:
        """Apply overrides to AI settings

        Args:
            profile: AI profile
            directives: AI directives
            override_name: Optional name override
            override_role: Optional role override
            replace_directives: Replace existing directives
            resources: Optional resource list
            constraints: Optional constraint list
            best_practices: Optional best practices list
            neural_protocols: Optional neural protocols
            quantum_protocols: Optional quantum protocols
            warfare_protocols: Optional warfare protocols
        """
        # Update profile
        if override_name:
            profile.name = override_name
            profile.modified_at = datetime.now()

        if override_role:
            if override_role == AIRole.WARRIOR and not self.allow_warfare:
                logger.warning("Warfare role not allowed")
                return

            profile.role = override_role
            profile.modified_at = datetime.now()

        # Update directives
        if replace_directives:
            if resources:
                directives.resources = resources
            if constraints:
                directives.constraints = constraints
            if best_practices:
                directives.best_practices = best_practices
            if neural_protocols:
                directives.neural_protocols = neural_protocols
            if quantum_protocols:
                directives.quantum_protocols = quantum_protocols
            if warfare_protocols and self.allow_warfare:
                directives.warfare_protocols = warfare_protocols
        else:
            if resources:
                directives.resources.extend(resources)
            if constraints:
                directives.constraints.extend(constraints)
            if best_practices:
                directives.best_practices.extend(best_practices)
            if neural_protocols:
                directives.neural_protocols.extend(neural_protocols)
            if quantum_protocols:
                directives.quantum_protocols.extend(quantum_protocols)
            if warfare_protocols and self.allow_warfare:
                directives.warfare_protocols.extend(warfare_protocols)

    async def interactively_configure(
        self,
        profile: AIProfile,
        directives: AIDirectives
    ) -> None:
        """Interactively configure AI settings

        Args:
            profile: AI profile to configure
            directives: AI directives to configure
        """
        revised = False

        while True:
            # Print current settings
            await self.print_settings(
                profile,
                directives,
                "Current Settings" if not revised else "Revised Settings"
            )

            if await input_handler.confirm("Continue with these settings?", default=True):
                break

            # Configure profile
            new_name = await input_handler.text(
                "Enter AI name",
                default=profile.name
            )
            if new_name:
                profile.name = new_name
                profile.modified_at = datetime.now()

            new_role = await input_handler.choice(
                "Select AI role",
                choices=[r.value for r in AIRole if r != AIRole.WARRIOR or self.allow_warfare],
                default=profile.role.value
            )
            if new_role:
                profile.role = AIRole(new_role)
                profile.modified_at = datetime.now()

            # Configure capabilities
            await self._configure_set(
                "capabilities",
                profile.capabilities,
                "Enter capability"
            )

            # Configure specializations
            await self._configure_set(
                "specializations",
                profile.specializations,
                "Enter specialization"
            )

            # Configure neural patterns
            if self.config.neural_enabled:
                await self._configure_set(
                    "neural patterns",
                    profile.neural_patterns,
                    "Enter neural pattern"
                )

            # Configure quantum states
            if self.config.quantum_enabled:
                await self._configure_set(
                    "quantum states",
                    profile.quantum_states,
                    "Enter quantum state"
                )

            # Configure directives
            await self._configure_list(
                "resources",
                directives.resources,
                "Enter resource"
            )

            await self._configure_list(
                "constraints",
                directives.constraints,
                "Enter constraint"
            )

            await self._configure_list(
                "best practices",
                directives.best_practices,
                "Enter best practice"
            )

            if self.config.neural_enabled:
                await self._configure_list(
                    "neural protocols",
                    directives.neural_protocols,
                    "Enter neural protocol"
                )

            if self.config.quantum_enabled:
                await self._configure_list(
                    "quantum protocols",
                    directives.quantum_protocols,
                    "Enter quantum protocol"
                )

            if self.allow_warfare:
                await self._configure_list(
                    "warfare protocols",
                    directives.warfare_protocols,
                    "Enter warfare protocol"
                )

            revised = True

    async def _configure_set(
        self,
        name: str,
        items: Set[str],
        prompt: str
    ) -> None:
        """Configure a set of items

        Args:
            name: Item type name
            items: Set to configure
            prompt: Input prompt
        """
        # Review existing items
        i = 0
        current = list(items)
        while i < len(current):
            item = current[i]
            console.print(f"{name.title()} {i+1}: {item}")

            action = await input_handler.choice(
                f"Keep {name}?",
                choices=["keep", "edit", "remove"],
                default="keep"
            )

            if action == "remove":
                items.remove(item)
                continue
            elif action == "edit":
                new_item = await input_handler.text(prompt)
                if new_item:
                    items.remove(item)
                    items.add(new_item)

            i += 1

        # Add new items
        while True:
            new_item = await input_handler.text(
                f"Enter new {name} (or press enter to finish)"
            )
            if not new_item:
                break

            items.add(new_item)

    async def _configure_list(
        self,
        name: str,
        items: List[str],
        prompt: str
    ) -> None:
        """Configure a list of items

        Args:
            name: Item type name
            items: List to configure
            prompt: Input prompt
        """
        # Review existing items
        i = 0
        while i < len(items):
            item = items[i]
            console.print(f"{name.title()} {i+1}: {item}")

            action = await input_handler.choice(
                f"Keep {name}?",
                choices=["keep", "edit", "remove"],
                default="keep"
            )

            if action == "remove":
                items.pop(i)
                continue
            elif action == "edit":
                new_item = await input_handler.text(prompt)
                if new_item:
                    items[i] = new_item

            i += 1

        # Add new items
        while True:
            new_item = await input_handler.text(
                f"Enter new {name} (or press enter to finish)"
            )
            if not new_item:
                break

            items.append(new_item)

    async def print_settings(
        self,
        profile: AIProfile,
        directives: AIDirectives,
        title: str = "AI Settings"
    ) -> None:
        """Print AI settings

        Args:
            profile: AI profile
            directives: AI directives
            title: Settings title
        """
        console.print(f"\n[bold]{title}[/]")
        console.print("-" * len(title))

        # Print profile
        console.print(f"[bold]Name:[/] {profile.name}")
        console.print(f"[bold]Role:[/] {profile.role.value}")
        console.print(f"[bold]Description:[/] {profile.description}")

        if profile.capabilities:
            console.print("\n[bold]Capabilities:[/]")
            for cap in profile.capabilities:
                console.print(f"- {cap}")

        if profile.specializations:
            console.print("\n[bold]Specializations:[/]")
            for spec in profile.specializations:
                console.print(f"- {spec}")

        if profile.neural_patterns:
            console.print("\n[bold]Neural Patterns:[/]")
            for pattern in profile.neural_patterns:
                console.print(f"- {pattern}")

        if profile.quantum_states:
            console.print("\n[bold]Quantum States:[/]")
            for state in profile.quantum_states:
                console.print(f"- {state}")

        # Print directives
        if directives.resources:
            console.print("\n[bold]Resources:[/]")
            for resource in directives.resources:
                console.print(f"- {resource}")

        if directives.constraints:
            console.print("\n[bold]Constraints:[/]")
            for constraint in directives.constraints:
                console.print(f"- {constraint}")

        if directives.best_practices:
            console.print("\n[bold]Best Practices:[/]")
            for practice in directives.best_practices:
                console.print(f"- {practice}")

        if directives.neural_protocols:
            console.print("\n[bold]Neural Protocols:[/]")
            for protocol in directives.neural_protocols:
                console.print(f"- {protocol}")

        if directives.quantum_protocols:
            console.print("\n[bold]Quantum Protocols:[/]")
            for protocol in directives.quantum_protocols:
                console.print(f"- {protocol}")

        if directives.warfare_protocols:
            console.print("\n[bold]Warfare Protocols:[/]")
            for protocol in directives.warfare_protocols:
                console.print(f"- {protocol}")

        console.print()

    async def save_profile(
        self,
        profile: AIProfile,
        directives: AIDirectives
    ) -> None:
        """Save AI profile and directives

        Args:
            profile: AI profile to save
            directives: AI directives to save
        """
        if not self.profile_dir:
            return

        profile_file = self.profile_dir / f"{profile.name}.json"

        data = {
            "profile": {
                "name": profile.name,
                "role": profile.role.value,
                "description": profile.description,
                "capabilities": list(profile.capabilities),
                "specializations": list(profile.specializations),
                "neural_patterns": list(profile.neural_patterns),
                "quantum_states": list(profile.quantum_states),
                "created_at": profile.created_at.isoformat(),
                "modified_at": profile.modified_at.isoformat()
            },
            "directives": {
                "resources": directives.resources,
                "constraints": directives.constraints,
                "best_practices": directives.best_practices,
                "neural_protocols": directives.neural_protocols,
                "quantum_protocols": directives.quantum_protocols,
                "warfare_protocols": directives.warfare_protocols
            }
        }

        with open(profile_file, "w") as f:
            json.dump(data, f, indent=2)

    async def load_profile(
        self,
        name: str
    ) -> Tuple[AIProfile, AIDirectives]:
        """Load AI profile and directives

        Args:
            name: Profile name to load

        Returns:
            Tuple of loaded profile and directives
        """
        if not self.profile_dir:
            raise ValueError("No profile directory configured")

        profile_file = self.profile_dir / f"{name}.json"
        if not profile_file.exists():
            raise ValueError(f"Profile {name} not found")

        with open(profile_file) as f:
            data = json.load(f)

        profile_data = data["profile"]
        profile = AIProfile(
            name=profile_data["name"],
            role=AIRole(profile_data["role"]),
            description=profile_data["description"],
            capabilities=set(profile_data["capabilities"]),
            specializations=set(profile_data["specializations"]),
            neural_patterns=set(profile_data["neural_patterns"]),
            quantum_states=set(profile_data["quantum_states"]),
            created_at=datetime.fromisoformat(profile_data["created_at"]),
            modified_at=datetime.fromisoformat(profile_data["modified_at"])
        )

        directives_data = data["directives"]
        directives = AIDirectives(
            resources=directives_data["resources"],
            constraints=directives_data["constraints"],
            best_practices=directives_data["best_practices"],
            neural_protocols=directives_data["neural_protocols"],
            quantum_protocols=directives_data["quantum_protocols"],
            warfare_protocols=directives_data["warfare_protocols"]
        )

        return profile, directives

# Global setup manager
setup_manager = SetupManager(NFXConfig())
