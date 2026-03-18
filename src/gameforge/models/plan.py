"""Data models for GameForge execution plans."""

from pydantic import BaseModel, Field


class Task(BaseModel):
    """A single task within a milestone."""

    id: str = Field(description="Unique task ID, e.g. '1.1'")
    title: str = Field(description="Short task description")
    description: str = Field(default="", description="Detailed task spec")
    depends_on: list[str] = Field(default_factory=list, description="Task IDs this depends on")
    agent: str = Field(default="designer", description="Primary agent: designer|coder|balancer")
    status: str = Field(default="pending", description="pending|in_progress|done|failed")


class PlaytestCriteria(BaseModel):
    """Criteria for passing a milestone's playtest."""

    description: str = Field(description="What must be true to pass")
    metric: str | None = Field(default=None, description="Metric to check, e.g. 'win_rate'")
    threshold: float | None = Field(default=None, description="Min value to pass")


class Milestone(BaseModel):
    """A milestone containing ordered tasks and playtest criteria."""

    id: str = Field(description="Milestone ID, e.g. '1'")
    title: str = Field(description="Milestone title")
    tasks: list[Task] = Field(default_factory=list)
    playtest: PlaytestCriteria | None = Field(default=None)
    status: str = Field(default="pending", description="pending|in_progress|done|failed")


class ExecutionPlan(BaseModel):
    """Full execution plan parsed from a GDD."""

    game_name: str
    gdd_path: str
    milestones: list[Milestone] = Field(default_factory=list)
    current_milestone: int = Field(default=0)
