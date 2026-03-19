"""Data models for GameForge execution plans."""

from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class AgentRole(str, Enum):
    DESIGNER = "designer"
    CRITIC = "critic"
    CODER = "coder"
    BALANCER = "balancer"
    PLAYTESTER = "playtester"


class Task(BaseModel):
    """A single task within a milestone."""

    id: str = Field(description="Unique task ID, e.g. '1.1'")
    title: str = Field(description="Short task description")
    description: str = Field(default="", description="Detailed task spec")
    depends_on: list[str] = Field(default_factory=list, description="Task IDs this depends on")
    primary_agent: AgentRole = Field(default=AgentRole.DESIGNER, description="Primary agent for this task")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    iterations: int = Field(default=0, description="How many design-code-test cycles this task took")
    max_iterations: int = Field(default=5, description="Max iterations before escalating to human")


class PlaytestCriteria(BaseModel):
    """Criteria for passing a milestone's playtest."""

    description: str = Field(description="What must be true to pass")
    metric: str | None = Field(default=None, description="Metric to check, e.g. 'win_rate'")
    threshold: float | None = Field(default=None, description="Min value to pass")
    operator: str = Field(default=">=", description="Comparison: >=, <=, ==, >, <")


class Milestone(BaseModel):
    """A milestone containing ordered tasks and playtest criteria."""

    id: str = Field(description="Milestone ID, e.g. '1'")
    title: str = Field(description="Milestone title")
    description: str = Field(default="", description="What this milestone achieves")
    tasks: list[Task] = Field(default_factory=list)
    playtest_criteria: list[PlaytestCriteria] = Field(default_factory=list)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    human_approved: bool | None = Field(default=None, description="None=not reviewed, True/False=decision")
    human_feedback: str = Field(default="", description="Feedback from human review")


class ExecutionPlan(BaseModel):
    """Full execution plan parsed from a GDD."""

    game_name: str
    gdd_path: str
    gdd_content: str = Field(default="", description="Raw GDD markdown content")
    milestones: list[Milestone] = Field(default_factory=list)
    current_milestone_idx: int = Field(default=0)

    @property
    def current_milestone(self) -> Milestone | None:
        if 0 <= self.current_milestone_idx < len(self.milestones):
            return self.milestones[self.current_milestone_idx]
        return None

    @property
    def is_complete(self) -> bool:
        return all(m.status == TaskStatus.DONE for m in self.milestones)
