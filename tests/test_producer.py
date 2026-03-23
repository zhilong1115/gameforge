"""Tests for Producer module (normalizer + plan generation)."""

from gameforge.producer.normalizer import analyze_gdd, normalize_gdd
from gameforge.producer.producer import produce_from_template
from gameforge.models.plan import AgentRole, ExecutionPlan


HU_GDD_PATH = "examples/hu/game_design.md"


def test_analyze_complete_gdd():
    with open(HU_GDD_PATH) as f:
        gdd = f.read()
    analysis = analyze_gdd(gdd)
    assert analysis.is_valid
    assert len(analysis.missing_required) == 0


def test_analyze_incomplete_gdd():
    gdd = "# My Game\nA simple platformer."
    analysis = analyze_gdd(gdd)
    assert not analysis.is_valid
    assert len(analysis.missing_required) > 0


def test_normalize_adds_missing_sections():
    gdd = "# My Game\nA simple platformer with jump mechanics."
    normalized = normalize_gdd(gdd)
    assert "Generated Sections" in normalized
    assert "TODO" in normalized


def test_normalize_complete_gdd_unchanged():
    with open(HU_GDD_PATH) as f:
        gdd = f.read()
    analysis = analyze_gdd(gdd)
    assert analysis.is_valid


def test_produce_from_template():
    plan = produce_from_template(HU_GDD_PATH)
    assert isinstance(plan, ExecutionPlan)
    assert plan.game.game_name == "HU"
    assert plan.game.game_type == "roguelike deck-builder mahjong"
    assert plan.game.game_framework == "phaser"
    assert len(plan.milestones) == 3
    assert plan.milestones[0].title == "Core Game Loop"


def test_produce_from_template_agents():
    plan = produce_from_template(HU_GDD_PATH)
    m1 = plan.milestones[0]
    roles = [a.role for a in m1.agents]
    assert AgentRole.DESIGNER in roles
    assert AgentRole.CODER in roles
    assert AgentRole.PLAYTESTER in roles
    assert AgentRole.CRITIC in roles


def test_produce_from_template_speaker_order():
    plan = produce_from_template(HU_GDD_PATH)
    m1 = plan.milestones[0]
    assert len(m1.speaker_order) > 0
    # Should start with designer and end with critic
    assert m1.speaker_order[0] == AgentRole.DESIGNER
    assert m1.speaker_order[-1] == AgentRole.CRITIC


def test_produce_from_template_dag():
    plan = produce_from_template(HU_GDD_PATH)
    assert plan.milestones[0].prerequisites == []
    assert plan.milestones[0].next == ["2"]
    assert plan.milestones[1].prerequisites == ["1"]
    errors = plan.validate_dag()
    assert errors == [], f"DAG errors: {errors}"


def test_produce_from_template_playtest():
    plan = produce_from_template(HU_GDD_PATH)
    m1 = plan.milestones[0]
    assert len(m1.playtest_criteria) > 0
    assert m1.playtest_criteria[0].threshold == 1.0


def test_produce_saves_json(tmp_path):
    output = str(tmp_path / "plan.json")
    plan = produce_from_template(HU_GDD_PATH, output_path=output)
    import json
    with open(output) as f:
        data = json.load(f)
    assert data["game"]["game_name"] == "HU"
    restored = ExecutionPlan.model_validate(data)
    assert len(restored.milestones) == 3
    assert len(restored.milestones[0].agents) > 0
