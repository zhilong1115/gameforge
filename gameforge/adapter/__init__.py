"""Game Adapter — optional headless interface for batch simulation.

Built by agents during the dev loop when statistical playtesting is needed.
This module defines the abstract interface; concrete adapters are game-specific.
"""

from .base import GameAdapter

__all__ = ["GameAdapter"]
