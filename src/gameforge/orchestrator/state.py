"""LangGraph state schema for GameForge."""

from typing import Any, TypedDict


class GameForgeState(TypedDict):
    """Global state shared across all LangGraph nodes."""

    # GDD
    gdd_content: str
    game_name: str

    # Plan
    milestones: list[dict[str, Any]]
    current_milestone_idx: int

    # Current task
    current_task_id: str | None
    design_spec: dict[str, Any] | None
    generated_code: dict[str, str]  # filename → code content

    # Playtest
    playtest_results: dict[str, Any] | None
    playtest_passed: bool

    # Balance
    balance_adjustments: list[dict[str, Any]]

    # Human review
    human_approved: bool | None
    human_feedback: str | None

    # History
    messages: list[dict[str, Any]]
    iteration_count: int
