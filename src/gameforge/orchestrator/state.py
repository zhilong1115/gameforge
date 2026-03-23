"""LangGraph state schema for GameForge."""

from typing import Any, TypedDict


class GameForgeState(TypedDict):
    """Global state shared across all LangGraph nodes."""

    # ── GDD ──
    gdd_content: str
    game_name: str

    # ── Plan ──
    # Milestone status tracked on Milestone.status (PENDING → READY → IN_PROGRESS → DONE/FAILED).
    # Use ExecutionPlan.ready_milestones() to find what can run next.
    execution_plan: dict[str, Any]  # Serialized ExecutionPlan
    current_milestone_id: str | None  # ID of milestone currently being executed

    # ── Design Phase ──
    design_spec: dict[str, Any] | None  # Serialized DesignSpec
    design_approved: bool

    # ── Code Phase ──
    generated_files: dict[str, str]  # filename → code content
    generated_tests: dict[str, str]  # test filename → test code
    code_approved: bool

    # ── Playtest Phase ──
    playtest_results: dict[str, Any] | None  # Serialized PlaytestResult
    playtest_passed: bool

    # ── Balance Phase ──
    balance_adjustments: list[dict[str, Any]]  # List of BalanceAdjustment

    # ── Human Review ──
    human_approved: bool | None  # None = not reviewed yet
    human_feedback: str

    # ── Control ──
    iteration_count: int
    max_iterations: int
    phase: str  # "design" | "code" | "playtest" | "balance" | "human_review"
    error: str | None

    # ── History ──
    messages: list[dict[str, Any]]  # Conversation history for context
