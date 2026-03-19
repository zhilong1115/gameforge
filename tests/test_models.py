"""Tests for GameForge data models."""

from gameforge.models import (
    AgentRole,
    BalanceAdjustment,
    CodeOutput,
    DesignSpec,
    ExecutionPlan,
    Milestone,
    PlaytestCriteria,
    PlaytestResult,
    Task,
    TaskStatus,
)


def test_task_defaults():
    task = Task(id="1.1", title="Create tile data structure")
    assert task.status == TaskStatus.PENDING
    assert task.primary_agent == AgentRole.DESIGNER
    assert task.depends_on == []
    assert task.iterations == 0


def test_task_with_dependencies():
    task = Task(
        id="1.3",
        title="Win detection",
        depends_on=["1.1", "1.2"],
        primary_agent=AgentRole.CODER,
    )
    assert task.depends_on == ["1.1", "1.2"]
    assert task.primary_agent == AgentRole.CODER


def test_playtest_criteria():
    criteria = PlaytestCriteria(
        description="Win rate between 45-55%",
        metric="win_rate",
        threshold=0.45,
        operator=">=",
    )
    assert criteria.metric == "win_rate"
    assert criteria.threshold == 0.45


def test_milestone():
    m = Milestone(
        id="1",
        title="Core Mahjong Round",
        tasks=[
            Task(id="1.1", title="Tile data structures"),
            Task(id="1.2", title="Draw/discard logic"),
            Task(id="1.3", title="Win detection", depends_on=["1.1", "1.2"]),
        ],
        playtest_criteria=[
            PlaytestCriteria(description="Can complete a basic round"),
        ],
    )
    assert len(m.tasks) == 3
    assert m.status == TaskStatus.PENDING
    assert m.human_approved is None


def test_execution_plan():
    plan = ExecutionPlan(
        game_name="HU",
        gdd_path="examples/hu/game_design.md",
        milestones=[
            Milestone(id="1", title="Core Round"),
            Milestone(id="2", title="Deck Building"),
        ],
    )
    assert plan.game_name == "HU"
    assert plan.current_milestone_idx == 0
    assert plan.current_milestone is not None
    assert plan.current_milestone.title == "Core Round"
    assert not plan.is_complete


def test_execution_plan_complete():
    plan = ExecutionPlan(
        game_name="HU",
        gdd_path="test.md",
        milestones=[
            Milestone(id="1", title="M1", status=TaskStatus.DONE),
            Milestone(id="2", title="M2", status=TaskStatus.DONE),
        ],
    )
    assert plan.is_complete


def test_design_spec():
    spec = DesignSpec(
        task_id="1.1",
        summary="136-tile mahjong deck with suits and honors",
        details="## Tile Class\n- suit: str\n- value: int\n...",
        data_structures=["Tile", "Deck", "Hand"],
        interfaces=["Deck.shuffle()", "Deck.draw() -> Tile"],
        approved_by_critic=True,
        discussion_rounds=3,
    )
    assert spec.approved_by_critic
    assert len(spec.data_structures) == 3


def test_code_output():
    code = CodeOutput(
        task_id="1.1",
        files={"tile.py": "class Tile:\n    pass"},
        tests={"test_tile.py": "def test_tile(): pass"},
        approved_by_critic=True,
    )
    assert "tile.py" in code.files
    assert code.approved_by_critic


def test_playtest_result():
    result = PlaytestResult(
        task_id="1.3",
        milestone_id="1",
        num_games=100,
        metrics={"win_rate": 0.48, "avg_rounds": 12.5},
        passed=True,
    )
    assert result.num_games == 100
    assert result.metrics["win_rate"] == 0.48
    assert result.passed


def test_balance_adjustment():
    adj = BalanceAdjustment(
        parameter="kan_multiplier",
        current_value=3.0,
        proposed_value=2.5,
        reasoning="Kan is too dominant, reducing multiplier for balance",
        approved_by_critic=True,
    )
    assert adj.proposed_value == 2.5
    assert adj.approved_by_critic
