"""Data models for GameForge execution plans."""

from enum import Enum

from pydantic import BaseModel, Field


# ── Enums ──


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


# ── Agent Config ──


class AgentConfig(BaseModel):
    """Per-agent config within a task."""

    role: AgentRole
    model: str = "default"  # references key in llm_config.json
    temperature: float = 0.7
    max_rounds: int = 10  # max AutoGen conversation rounds
    system_prompt: str = ""  # additional prompt injection


# ── Task ──


class Task(BaseModel):
    """A single task within a milestone, executed as an AutoGen GroupChat."""

    id: str = Field(description="Unique task ID, e.g. '1.1'")
    title: str = Field(description="Short task description")
    description: str = Field(default="", description="Detailed task spec")
    depends_on: list[str] = Field(default_factory=list, description="Task IDs this depends on")
    agents: list[AgentConfig] = Field(default_factory=list, description="Agents participating in this task")
    max_iterations: int = Field(default=5, description="Max design-code-test cycles")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    iterations: int = Field(default=0, description="Current iteration count")


# ── Playtest ──


class PlaytestCriteria(BaseModel):
    """Criteria for passing a milestone's playtest."""

    description: str = Field(description="What must be true to pass")
    metric: str | None = Field(default=None, description="Metric to check, e.g. 'win_rate'")
    threshold: float | None = Field(default=None, description="Value to compare against")
    operator: str = Field(default=">=", description="Comparison: >=, <=, ==, >, <")


# ── Milestone ──


class Milestone(BaseModel):
    """A milestone — executed as a LangGraph node containing multiple AutoGen tasks.
    
    DAG structure is defined by `prerequisites` and `next`:
    - prerequisites: milestone IDs that must ALL complete before this one starts
    - next: milestone IDs that this one unlocks when complete
    
    These should be mirrors of each other (if A.next contains B, then B.prerequisites contains A).
    Use `ExecutionPlan.validate_dag()` to check consistency.
    """

    id: str = Field(description="Milestone ID, e.g. '1'")
    title: str = Field(description="Milestone title")
    description: str = Field(default="", description="What this milestone achieves")
    prerequisites: list[str] = Field(default_factory=list, description="Milestone IDs that must complete before this starts")
    next: list[str] = Field(default_factory=list, description="Milestone IDs unlocked when this completes")
    programming_language: str = Field(default="python", description="Language for code generation in this milestone")
    tasks: list[Task] = Field(default_factory=list)
    playtest_criteria: list[PlaytestCriteria] = Field(default_factory=list)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    human_approved: bool | None = Field(default=None, description="None=not reviewed, True/False=decision")
    human_feedback: str = Field(default="", description="Feedback from human review")


# ── Game Config ──


class GameConfig(BaseModel):
    """Game metadata — passed as system context to all agents."""

    # Basic info
    game_name: str
    gdd_path: str
    game_type: str = Field(description="e.g. 'roguelike', 'deck-builder', 'RPG'")
    description: str = Field(default="", description="One-line game description")
    supported_languages: list[str] = Field(default=["en"], description="e.g. ['en', 'zh', 'ja']")

    # Technical info
    target_platforms: list[str] = Field(description="e.g. ['web', 'mobile', 'desktop']")
    game_framework: str = Field(default="", description="e.g. 'phaser', 'pygame', 'godot'")
    art_style: str = Field(default="", description="e.g. 'pixel', '3d', '2d-cartoon', 'ascii'")
    output_dir: str = Field(default="./output", description="Where generated code goes")


# ── Execution Plan ──

# Note: ExecutionPlan is kept for backwards compatibility and overview,
# but the primary output format is now:
#   - gdd_normalized.md (system prompt for all agents)
#   - milestone_N.json (one per milestone, each is an AutoGen GroupChat config)


class ExecutionPlan(BaseModel):
    """Overview of all milestones. Used for planning, not execution.
    
    For execution, each Milestone is saved as a separate JSON file
    and the normalized GDD.md serves as shared system context.
    """

    # Game config (extracted from GDD, used for overview)
    game: GameConfig

    # Config paths
    llm_config_path: str = Field(default="./llm_config.json", description="Path to LLM credentials config")
    custom_skills_dir: str | None = Field(default=None, description="Path to user-provided skills directory")

    # Milestones
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

    def _milestone_map(self) -> dict[str, Milestone]:
        """Build a quick lookup: milestone ID → Milestone."""
        return {m.id: m for m in self.milestones}

    def ready_milestones(self) -> list[Milestone]:
        """Return milestones whose prerequisites are all DONE and that are still PENDING.
        
        These can be executed in parallel by LangGraph.
        """
        mm = self._milestone_map()
        ready = []
        for m in self.milestones:
            if m.status != TaskStatus.PENDING:
                continue
            if all(mm[pid].status == TaskStatus.DONE for pid in m.prerequisites if pid in mm):
                ready.append(m)
        return ready

    def validate_dag(self) -> list[str]:
        """Validate DAG consistency. Returns list of errors (empty = valid).
        
        Checks:
        1. All referenced milestone IDs exist
        2. prerequisites and next are mirrors of each other
        3. No cycles (topological sort)
        """
        errors = []
        mm = self._milestone_map()
        valid_ids = set(mm.keys())

        # Check references exist
        for m in self.milestones:
            for pid in m.prerequisites:
                if pid not in valid_ids:
                    errors.append(f"Milestone '{m.id}' has unknown prerequisite '{pid}'")
            for nid in m.next:
                if nid not in valid_ids:
                    errors.append(f"Milestone '{m.id}' has unknown next '{nid}'")

        # Check mirror consistency: if A.next has B, then B.prerequisites has A
        for m in self.milestones:
            for nid in m.next:
                if nid in mm and m.id not in mm[nid].prerequisites:
                    errors.append(f"Milestone '{m.id}' lists '{nid}' in next, but '{nid}' doesn't list '{m.id}' in prerequisites")
            for pid in m.prerequisites:
                if pid in mm and m.id not in mm[pid].next:
                    errors.append(f"Milestone '{m.id}' lists '{pid}' in prerequisites, but '{pid}' doesn't list '{m.id}' in next")

        # Check no cycles (Kahn's algorithm)
        in_degree = {m.id: len(m.prerequisites) for m in self.milestones}
        queue = [mid for mid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            mid = queue.pop(0)
            visited += 1
            for nid in mm[mid].next:
                if nid in in_degree:
                    in_degree[nid] -= 1
                    if in_degree[nid] == 0:
                        queue.append(nid)
        if visited != len(self.milestones):
            errors.append("Cycle detected in milestone DAG")

        return errors

    def save_milestones(self, output_dir: str = "./output") -> list[str]:
        """Save each milestone as a separate JSON file.
        
        Returns list of file paths created.
        """
        from pathlib import Path
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths = []
        for m in self.milestones:
            filename = f"milestone_{m.id}_{m.title.lower().replace(' ', '_')}.json"
            filepath = out / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(m.model_dump_json(indent=2))
            paths.append(str(filepath))
        return paths
