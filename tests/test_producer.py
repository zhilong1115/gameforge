"""Tests for Producer module (normalizer + plan generation)."""

from gameforge.producer.normalizer import analyze_gdd, normalize_gdd
from gameforge.producer.producer import produce_from_template
from gameforge.models.plan import ExecutionPlan, GameConfig


HU_GDD_PATH = "examples/hu/game_design.md"


def test_analyze_complete_gdd():
    with open(HU_GDD_PATH) as f:
        gdd = f.read()
    analysis = analyze_gdd(gdd)
    assert analysis.is_valid  # HU GDD has all required sections
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
    # HU has all required, only missing art_style and agent_config
    assert analysis.is_valid


def test_produce_from_template():
    plan = produce_from_template(HU_GDD_PATH)
    assert isinstance(plan, ExecutionPlan)
    assert plan.game.game_name == "HU"
    assert plan.game.game_type == "roguelike deck-builder mahjong"
    assert plan.game.game_framework == "phaser"
    assert len(plan.milestones) == 3
    assert plan.milestones[0].title == "Core Game Loop"


def test_produce_from_template_tasks():
    plan = produce_from_template(HU_GDD_PATH)
    m1 = plan.milestones[0]
    assert len(m1.tasks) == 3
    assert m1.tasks[0].id == "1.1"
    assert m1.tasks[1].depends_on == ["1.1"]
    assert m1.tasks[2].depends_on == ["1.1", "1.2"]


def test_produce_from_template_agents():
    plan = produce_from_template(HU_GDD_PATH)
    task = plan.milestones[0].tasks[0]  # 1.1: Data structures
    roles = [a.role.value for a in task.agents]
    assert "designer" in roles
    assert "critic" in roles


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
