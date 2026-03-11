"""Tests for the Producer agent."""

import json
import pytest
from pathlib import Path

from gameforge.models.plan import ExecutionPlan, Milestone, AgentConfig, GameConfig, PlaytestMode


class TestExecutionPlanModel:
    """Test that the data models serialize/deserialize correctly."""

    def test_minimal_plan(self):
        plan = ExecutionPlan(
            game=GameConfig(name="TestGame", genre="Puzzle", platform="Web"),
            agents={
                "designer": AgentConfig(role="designer", system_context="You design puzzles"),
                "implementer": AgentConfig(role="implementer", system_context="You code puzzles"),
                "playtester": AgentConfig(role="playtester", system_context="You test puzzles"),
            },
            milestones=[
                Milestone(id=1, name="MVP", goal="Basic puzzle works", exit_criteria=["Can complete one puzzle"]),
            ],
        )
        
        # Roundtrip JSON
        json_str = plan.model_dump_json()
        plan2 = ExecutionPlan.model_validate_json(json_str)
        assert plan2.game.name == "TestGame"
        assert len(plan2.milestones) == 1
        assert len(plan2.agents) == 3

    def test_plan_with_adapter(self):
        plan = ExecutionPlan(
            game=GameConfig(name="HU", genre="Roguelike", platform="Web", stack={"engine": "Phaser 3"}),
            agents={
                "designer": AgentConfig(role="designer", system_context="Design mahjong content"),
                "implementer": AgentConfig(role="implementer", system_context="Build the game"),
                "playtester": AgentConfig(role="playtester", system_context="Play and test"),
            },
            milestones=[
                Milestone(id=1, name="Core", goal="Playable hand", exit_criteria=["Hand completes"]),
                Milestone(id=2, name="Balance", goal="Balanced content", exit_criteria=["Win rates OK"],
                         playtest_mode=PlaytestMode.ADAPTER, adapter_hint="Build headless engine"),
            ],
            adapter_needed=True,
            adapter_reason="Game has numerical balance needs",
        )
        
        assert plan.adapter_needed is True
        assert plan.milestones[1].playtest_mode == PlaytestMode.ADAPTER

    def test_json_schema(self):
        """The JSON schema should be valid and usable for LLM structured output."""
        schema = ExecutionPlan.model_json_schema()
        assert "properties" in schema
        assert "game" in schema["properties"]
        assert "milestones" in schema["properties"]


class TestProducer:
    """Tests for Producer.generate_plan() — implement after writing Producer."""

    @pytest.mark.skip(reason="Implement Producer first")
    def test_generate_plan_from_hu_design(self):
        """Producer should generate a valid plan from HU's game_design.md."""
        from gameforge.producer import Producer
        from gameforge.tools.llm import AnthropicClient

        producer = Producer(llm=AnthropicClient())
        plan = producer.generate_plan("examples/hu/game_design.md")

        assert plan.game.name.lower() in ["hu", "hu!"]
        assert len(plan.milestones) >= 2
        assert plan.adapter_needed is True  # HU has balance needs
        assert all(role in plan.agents for role in ["designer", "implementer", "playtester"])

    @pytest.mark.skip(reason="Implement Producer first")
    def test_validation_catches_bad_plan(self):
        """Validation should flag plans with missing/invalid fields."""
        from gameforge.producer import Producer
        from gameforge.tools.llm import AnthropicClient

        producer = Producer(llm=AnthropicClient())
        
        bad_plan = ExecutionPlan(
            game=GameConfig(name="", genre="", platform=""),
            agents={},
            milestones=[],
        )
        errors = producer._validate_plan(bad_plan)
        assert len(errors) > 0  # Should have multiple validation errors
