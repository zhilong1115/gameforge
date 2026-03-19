"""Data models for design specs and agent outputs."""

from pydantic import BaseModel, Field


class DesignSpec(BaseModel):
    """Output from Designer + Critic discussion."""

    task_id: str = Field(description="Which task this design is for")
    summary: str = Field(description="One-line summary of the design")
    details: str = Field(description="Full design specification in markdown")
    data_structures: list[str] = Field(default_factory=list, description="Key data structures to implement")
    interfaces: list[str] = Field(default_factory=list, description="Function/class interfaces")
    constraints: list[str] = Field(default_factory=list, description="Constraints and edge cases")
    approved_by_critic: bool = Field(default=False, description="Whether Critic approved this design")
    discussion_rounds: int = Field(default=0, description="How many rounds of discussion")


class CodeOutput(BaseModel):
    """Output from Coder agent."""

    task_id: str
    files: dict[str, str] = Field(default_factory=dict, description="filename → code content")
    tests: dict[str, str] = Field(default_factory=dict, description="test filename → test code")
    approved_by_critic: bool = Field(default=False)
    review_comments: list[str] = Field(default_factory=list)


class PlaytestResult(BaseModel):
    """Output from Playtester (algorithmic simulation)."""

    task_id: str
    milestone_id: str
    num_games: int = Field(description="Number of games simulated")
    metrics: dict[str, float] = Field(default_factory=dict, description="metric_name → value")
    passed: bool = Field(default=False, description="Whether all criteria were met")
    details: str = Field(default="", description="Detailed playtest report")


class BalanceAdjustment(BaseModel):
    """Output from Balancer agent."""

    parameter: str = Field(description="What to adjust, e.g. 'kan_multiplier'")
    current_value: float | str
    proposed_value: float | str
    reasoning: str = Field(description="Why this change improves balance")
    approved_by_critic: bool = Field(default=False)
