"""Tests for GameForge data models."""

from gameforge.models import (
    AgentConfig,
    AgentRole,
    BalanceAdjustment,
    CodeOutput,
    DesignSpec,
    ExecutionPlan,
    GameConfig,
    Milestone,
    PlaytestCriteria,
    PlaytestResult,
    Task,
    TaskStatus,
)


# ── GameConfig ──


def test_game_config():
    config = GameConfig(
        game_name="HU",
        gdd_path="examples/hu/game_design.md",
        game_type="roguelike deck-builder",
        target_platforms=["web"],
        game_framework="phaser",
        art_style="pixel",
    )
    assert config.game_name == "HU"
    assert config.supported_languages == ["en"]
    assert config.output_dir == "./output"


def test_game_config_json_roundtrip():
    config = GameConfig(
        game_name="HU",
        gdd_path="test.md",
        game_type="roguelike",
        target_platforms=["web", "mobile"],
    )
    json_str = config.model_dump_json()
    restored = GameConfig.model_validate_json(json_str)
    assert restored.game_name == "HU"
    assert restored.target_platforms == ["web", "mobile"]


# ── AgentConfig ──


def test_agent_config_defaults():
    agent = AgentConfig(role=AgentRole.DESIGNER)
    assert agent.model == "default"
    assert agent.temperature == 0.7
    assert agent.max_rounds == 10


def test_agent_config_custom():
    agent = AgentConfig(
        role=AgentRole.CODER,
        model="fast",
        temperature=0.3,
        max_rounds=5,
    )
    assert agent.role == AgentRole.CODER
    assert agent.model == "fast"


# ── Task ──


def test_task_defaults():
    task = Task(id="1.1", title="Create tile data structure")
    assert task.status == TaskStatus.PENDING
    assert task.agents == []
    assert task.depends_on == []
    assert task.iterations == 0


def test_task_with_agents():
    task = Task(
        id="1.1",
        title="Design tile system",
        agents=[
            AgentConfig(role=AgentRole.DESIGNER),
            AgentConfig(role=AgentRole.CRITIC, temperature=0.3),
        ],
    )
    assert len(task.agents) == 2
    assert task.agents[0].role == AgentRole.DESIGNER
    assert task.agents[1].temperature == 0.3


def test_task_with_dependencies():
    task = Task(
        id="1.3",
        title="Win detection",
        depends_on=["1.1", "1.2"],
    )
    assert task.depends_on == ["1.1", "1.2"]


# ── Milestone ──


def test_milestone():
    m = Milestone(
        id="1",
        title="Core Mahjong Round",
        programming_language="python",
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
    assert m.programming_language == "python"
    assert m.status == TaskStatus.PENDING
    assert m.human_approved is None


# ── ExecutionPlan ──


def test_execution_plan():
    plan = ExecutionPlan(
        game=GameConfig(
            game_name="HU",
            gdd_path="examples/hu/game_design.md",
            game_type="roguelike deck-builder",
            target_platforms=["web"],
        ),
        milestones=[
            Milestone(id="1", title="Core Round"),
            Milestone(id="2", title="Deck Building"),
        ],
    )
    assert plan.game.game_name == "HU"
    assert plan.current_milestone_idx == 0
    assert plan.current_milestone is not None
    assert plan.current_milestone.title == "Core Round"
    assert not plan.is_complete


def test_execution_plan_complete():
    plan = ExecutionPlan(
        game=GameConfig(
            game_name="HU",
            gdd_path="test.md",
            game_type="roguelike",
            target_platforms=["web"],
        ),
        milestones=[
            Milestone(id="1", title="M1", status=TaskStatus.DONE),
            Milestone(id="2", title="M2", status=TaskStatus.DONE),
        ],
    )
    assert plan.is_complete


def test_execution_plan_with_skills():
    plan = ExecutionPlan(
        game=GameConfig(
            game_name="HU",
            gdd_path="test.md",
            game_type="roguelike",
            target_platforms=["web"],
        ),
        custom_skills_dir="./my_skills",
    )
    assert plan.custom_skills_dir == "./my_skills"
    assert plan.llm_config_path == "./llm_config.json"


def test_execution_plan_json_roundtrip():
    plan = ExecutionPlan(
        game=GameConfig(
            game_name="HU",
            gdd_path="test.md",
            game_type="roguelike",
            target_platforms=["web"],
            game_framework="phaser",
        ),
        milestones=[
            Milestone(
                id="1",
                title="Core Round",
                programming_language="typescript",
                tasks=[
                    Task(
                        id="1.1",
                        title="Tiles",
                        agents=[AgentConfig(role=AgentRole.DESIGNER)],
                    ),
                ],
            ),
        ],
    )
    json_str = plan.model_dump_json(indent=2)
    restored = ExecutionPlan.model_validate_json(json_str)
    assert restored.game.game_name == "HU"
    assert restored.milestones[0].programming_language == "typescript"
    assert restored.milestones[0].tasks[0].agents[0].role == AgentRole.DESIGNER


# ── Design Models ──


def test_design_spec():
    spec = DesignSpec(
        task_id="1.1",
        summary="136-tile mahjong deck with suits and honors",
        details="## Tile Class\n- suit: str\n- value: int",
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


def test_playtest_result():
    result = PlaytestResult(
        task_id="1.3",
        milestone_id="1",
        num_games=100,
        metrics={"win_rate": 0.48, "avg_rounds": 12.5},
        passed=True,
    )
    assert result.metrics["win_rate"] == 0.48


def test_balance_adjustment():
    adj = BalanceAdjustment(
        parameter="kan_multiplier",
        current_value=3.0,
        proposed_value=2.5,
        reasoning="Kan is too dominant",
        approved_by_critic=True,
    )
    assert adj.proposed_value == 2.5
