"""Data models for GameForge execution plans."""

from enum import Enum

from pydantic import BaseModel, Field


# ── Enums ──


class MilestoneStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"  # all prerequisites met, can be executed
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
    """AutoGen agent configuration within a milestone's GroupChat."""

    role: AgentRole
    model: str = "default"  # references key in llm_config.json
    temperature: float = 0.7
    system_prompt: str = ""  # task-specific prompt injection


# ── Playtest ──


class PlaytestCriteria(BaseModel):
    """Criteria for passing a milestone's playtest."""

    description: str = Field(description="What must be true to pass")
    metric: str | None = Field(default=None, description="Metric to check, e.g. 'win_rate'")
    threshold: float | None = Field(default=None, description="Value to compare against")
    operator: str = Field(default=">=", description="Comparison: >=, <=, ==, >, <")


# ── Milestone ──


class Milestone(BaseModel):
    """A milestone — the atomic execution unit in GameForge.
    
    Each milestone maps directly to one AutoGen GroupChat session.
    The DAG structure (prerequisites/next) determines execution order.
    
    Lifecycle: PENDING → READY → IN_PROGRESS → DONE / FAILED
    """

    # Identity
    id: str = Field(description="Milestone ID, e.g. '1'")
    title: str = Field(description="Milestone title")
    description: str = Field(default="", description="What this milestone achieves")

    # DAG edges
    prerequisites: list[str] = Field(default_factory=list, description="Milestone IDs that must complete before this starts")
    next: list[str] = Field(default_factory=list, description="Milestone IDs unlocked when this completes")

    # AutoGen GroupChat config
    agents: list[AgentConfig] = Field(default_factory=list, description="Agents in this GroupChat")
    speaker_order: list[AgentRole] = Field(default_factory=list, description="Agent speaking sequence, e.g. [designer, critic, coder, critic]")
    manager_model: str = Field(default="default", description="LLM config key for the GroupChatManager")
    max_rounds: int = Field(default=20, description="Max conversation rounds in the GroupChat")

    # Execution config
    programming_language: str = Field(default="python", description="Language for code generation")
    max_iterations: int = Field(default=5, description="Max retry cycles (design→code→test)")
    iterations: int = Field(default=0, description="Current iteration count")

    # Quality gate
    playtest_criteria: list[PlaytestCriteria] = Field(default_factory=list)

    # Status
    status: MilestoneStatus = Field(default=MilestoneStatus.PENDING)
    human_approved: bool | None = Field(default=None, description="None=not reviewed, True/False=decision")
    human_feedback: str = Field(default="", description="Feedback from human review")


# ── Game Config ──


class GameConfig(BaseModel):
    """Game metadata — passed as system context to all agents."""

    game_name: str
    gdd_path: str
    game_type: str = Field(description="e.g. 'roguelike', 'deck-builder', 'RPG'")
    description: str = Field(default="", description="One-line game description")
    supported_languages: list[str] = Field(default=["en"], description="e.g. ['en', 'zh', 'ja']")

    target_platforms: list[str] = Field(description="e.g. ['web', 'mobile', 'desktop']")
    game_framework: str = Field(default="", description="e.g. 'phaser', 'pygame', 'godot'")
    art_style: str = Field(default="", description="e.g. 'pixel', '3d', '2d-cartoon', 'ascii'")
    output_dir: str = Field(default="./output", description="Where generated code goes")


# ── Execution Plan ──


class ExecutionPlan(BaseModel):
    """The full milestone DAG for building a game.
    
    Each Milestone is saved as a separate JSON file that doubles as
    an AutoGen GroupChat config. The normalized GDD serves as shared
    system context for all agents.
    """

    game: GameConfig

    # Config paths
    llm_config_path: str = Field(default="./llm_config.json", description="Path to LLM credentials config")
    custom_skills_dir: str | None = Field(default=None, description="Path to user-provided tools")

    # Milestones
    milestones: list[Milestone] = Field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return all(m.status == MilestoneStatus.DONE for m in self.milestones)

    def _milestone_map(self) -> dict[str, Milestone]:
        return {m.id: m for m in self.milestones}

    def ready_milestones(self) -> list[Milestone]:
        """Find milestones whose prerequisites are all DONE, mark them READY, and return them."""
        mm = self._milestone_map()
        ready = []
        for m in self.milestones:
            if m.status != MilestoneStatus.PENDING:
                if m.status == MilestoneStatus.READY:
                    ready.append(m)
                continue
            if all(mm[pid].status == MilestoneStatus.DONE for pid in m.prerequisites if pid in mm):
                m.status = MilestoneStatus.READY
                ready.append(m)
        return ready

    def validate_dag(self) -> list[str]:
        """Validate DAG consistency. Returns list of errors (empty = valid)."""
        errors = []
        mm = self._milestone_map()
        valid_ids = set(mm.keys())

        for m in self.milestones:
            for pid in m.prerequisites:
                if pid not in valid_ids:
                    errors.append(f"Milestone '{m.id}' has unknown prerequisite '{pid}'")
            for nid in m.next:
                if nid not in valid_ids:
                    errors.append(f"Milestone '{m.id}' has unknown next '{nid}'")

        for m in self.milestones:
            for nid in m.next:
                if nid in mm and m.id not in mm[nid].prerequisites:
                    errors.append(f"Milestone '{m.id}' lists '{nid}' in next, but '{nid}' doesn't list '{m.id}' in prerequisites")
            for pid in m.prerequisites:
                if pid in mm and m.id not in mm[pid].next:
                    errors.append(f"Milestone '{m.id}' lists '{pid}' in prerequisites, but '{pid}' doesn't list '{m.id}' in next")

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
