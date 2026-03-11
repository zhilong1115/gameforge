"""Feedback models for the dev loop.

Playtester produces Feedback; routing logic sends it to the right agent.
"""

from pydantic import BaseModel
from enum import Enum


class FeedbackType(str, Enum):
    BUG = "bug"           # → Implementer
    BORING = "boring"     # → Designer
    TOO_HARD = "too_hard" # → Designer
    TOO_EASY = "too_easy" # → Designer
    PASS = "pass"         # → Milestone check


# Routing table: which agent handles which feedback type
FEEDBACK_ROUTING: dict[FeedbackType, str] = {
    FeedbackType.BUG: "implementer",
    FeedbackType.BORING: "designer",
    FeedbackType.TOO_HARD: "designer",
    FeedbackType.TOO_EASY: "designer",
    FeedbackType.PASS: "_milestone_check",
}


class Feedback(BaseModel):
    """Structured feedback from the Playtester."""
    type: FeedbackType
    summary: str              # One-line description
    details: str              # Full explanation
    severity: int = 5         # 1-10, higher = more critical
    reproduction_steps: str | None = None  # For bugs
    milestone_criteria_met: list[str] | None = None  # For PASS: which criteria are satisfied
