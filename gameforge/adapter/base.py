"""Abstract Game Adapter interface.

Concrete adapters are built by the Implementer agent during the dev loop.
This defines what they must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class GameAdapter(ABC):
    """Headless interface to a game engine for batch simulation."""

    @property
    @abstractmethod
    def game_name(self) -> str:
        ...

    @abstractmethod
    def content_schema(self) -> dict:
        """JSON Schema for valid content configurations."""
        ...

    @abstractmethod
    def balance_targets(self) -> dict:
        """Target metric ranges (e.g., win rates per difficulty)."""
        ...

    @abstractmethod
    def simulate(
        self,
        config: dict,
        n_episodes: int = 1000,
        seeds: list[int] | None = None,
    ) -> dict:
        """Run n_episodes with the given config, return statistics."""
        ...

    @abstractmethod
    def classify_build(self, episode: dict) -> str:
        """Classify a single episode into a strategy archetype."""
        ...

    @abstractmethod
    def export(self, config: dict, output_dir: str) -> list[str]:
        """Export accepted config to game-native files. Returns file paths."""
        ...
