"""Producer — reads a GDD and generates an ExecutionPlan (milestone DAG).

The Producer calls an LLM to:
1. Extract game metadata (GameConfig)
2. Break the game into milestones with agent assignments
3. Define DAG dependencies (prerequisites/next)
4. Define playtest criteria per milestone

Output: a validated ExecutionPlan where each Milestone is an AutoGen GroupChat config.
"""

import json
from pathlib import Path

from gameforge.models.plan import (
    AgentConfig,
    AgentRole,
    ExecutionPlan,
    GameConfig,
    Milestone,
    MilestoneStatus,
    PlaytestCriteria,
)
from gameforge.agents import AGENTS


# ── LLM Prompt for Plan Generation ──

PLAN_GENERATION_PROMPT = """You are a game development Producer. Read the Game Design Document (GDD) below and create a structured execution plan.

Your output must be valid JSON matching this schema:

{{
  "game": {{
    "game_name": "string",
    "gdd_path": "string",
    "game_type": "string (e.g. roguelike, deck-builder)",
    "description": "one-line description",
    "supported_languages": ["en"],
    "target_platforms": ["web", "mobile", etc.],
    "game_framework": "string (e.g. phaser, godot, pygame)",
    "art_style": "string (e.g. pixel, 2d-cartoon, ascii)",
    "output_dir": "./output"
  }},
  "milestones": [
    {{
      "id": "1",
      "title": "string",
      "description": "what this milestone achieves",
      "prerequisites": [],
      "next": ["2", "3"],
      "programming_language": "typescript",
      "agents": [
        {{
          "role": "designer",
          "temperature": 0.7,
          "system_prompt": "specific instructions for this milestone"
        }},
        {{
          "role": "critic",
          "temperature": 0.3
        }},
        {{
          "role": "coder",
          "temperature": 0.3
        }}
      ],
      "speaker_order": ["designer", "critic", "coder", "critic"],
      "manager_model": "default",
      "max_rounds": 20,
      "max_iterations": 5,
      "playtest_criteria": [
        {{
          "description": "what must be true to pass",
          "metric": "metric_name",
          "threshold": 0.5,
          "operator": ">="
        }}
      ]
    }}
  ]
}}

### Planning Rules:

1. **Start minimal** — Milestone 1 should be the simplest playable version
2. **Each milestone = one GroupChat** — keep milestones small and focused
3. **DAG, not linear** — milestones that don't depend on each other can run in parallel
4. **prerequisites + next must be mirrors** — if 1.next has 2, then 2.prerequisites has 1
5. **Every milestone gets agents** — at minimum Designer + Critic, or Coder + Critic
6. **speaker_order defines conversation flow** — e.g. [designer, critic, coder, critic]
7. **Playtest criteria are measurable** — "can complete a round", "win rate > 40%"

### Agent Roles:
- **designer**: designs mechanics, data structures, rules
- **critic**: reviews all proposals, finds edge cases
- **coder**: writes code from design specs
- **playtester**: runs game simulations via tool calls, reports statistics
- **balancer**: analyzes playtest data, proposes adjustments

---

GDD:

{gdd_content}

---

Generate the execution plan JSON. Be specific to THIS game, not generic."""


def read_gdd(gdd_path: str) -> str:
    """Read a GDD markdown file."""
    path = Path(gdd_path)
    if not path.exists():
        raise FileNotFoundError(f"GDD not found: {gdd_path}")
    return path.read_text(encoding="utf-8")


def generate_plan_with_llm(gdd_content: str, gdd_path: str, llm_fn=None) -> ExecutionPlan:
    """Generate an ExecutionPlan by calling an LLM."""
    prompt = PLAN_GENERATION_PROMPT.format(gdd_content=gdd_content)
    
    if llm_fn is None:
        try:
            import requests
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=120,
            )
            raw_json = resp.json().get("response", "")
        except Exception:
            raise RuntimeError(
                "No LLM available. Either start ollama or pass a custom llm_fn."
            )
    else:
        raw_json = llm_fn(prompt)
    
    plan_data = json.loads(raw_json)
    if "game" in plan_data:
        plan_data["game"]["gdd_path"] = gdd_path
    
    plan = ExecutionPlan.model_validate(plan_data)
    return plan


def produce(gdd_path: str, llm_fn=None, output_path: str | None = None) -> ExecutionPlan:
    """Main entry point: read GDD → generate plan → optionally save."""
    gdd_content = read_gdd(gdd_path)
    plan = generate_plan_with_llm(gdd_content, gdd_path, llm_fn)
    
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))
        print(f"Plan saved to: {output_path}")
    
    return plan


def produce_full(
    gdd_path: str,
    output_dir: str = "./output",
    llm_fn=None,
) -> tuple[str, list[str]]:
    """Full pipeline: normalize GDD → generate milestones → save all files."""
    from gameforge.producer.normalizer import normalize_gdd
    
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    gdd_content = read_gdd(gdd_path)
    gdd_normalized_path = str(out / "gdd_normalized.md")
    normalize_gdd(gdd_content, output_path=gdd_normalized_path, llm_fn=llm_fn)
    
    if llm_fn:
        plan = generate_plan_with_llm(gdd_content, gdd_path, llm_fn)
    else:
        plan = produce_from_template(gdd_path)
    
    milestone_paths = plan.save_milestones(output_dir)
    
    overview_path = str(out / "plan_overview.json")
    with open(overview_path, "w", encoding="utf-8") as f:
        f.write(plan.model_dump_json(indent=2))
    
    print(f"\nProducer output ({output_dir}):")
    print(f"  System prompt: {gdd_normalized_path}")
    print(f"  Milestones: {len(milestone_paths)} files")
    for p in milestone_paths:
        print(f"    - {p}")
    print(f"  Overview: {overview_path}")
    
    return gdd_normalized_path, milestone_paths


# ── Fallback: Rule-based plan generation (no LLM needed) ──

def produce_from_template(gdd_path: str, output_path: str | None = None) -> ExecutionPlan:
    """Generate a plan using templates instead of LLM.
    
    Useful for testing or when no LLM is available.
    """
    gdd_content = read_gdd(gdd_path)
    
    lines = gdd_content.split("\n")
    title = lines[0].replace("#", "").strip() if lines else "Unknown Game"
    
    framework = ""
    language = "python"
    platforms = ["web"]
    art_style = ""
    game_type = ""
    
    content_lower = gdd_content.lower()
    if "phaser" in content_lower:
        framework = "phaser"
        language = "typescript"
    elif "godot" in content_lower:
        framework = "godot"
        language = "gdscript"
    elif "pygame" in content_lower:
        framework = "pygame"
    
    if "roguelike" in content_lower:
        game_type += "roguelike "
    if "deck-builder" in content_lower or "deck builder" in content_lower:
        game_type += "deck-builder "
    if "mahjong" in content_lower:
        game_type += "mahjong "
    game_type = game_type.strip() or "game"
    
    if "pixel" in content_lower:
        art_style = "pixel"
    elif "2d" in content_lower:
        art_style = "2d"
    if "mobile" in content_lower:
        platforms.append("mobile")
    
    game_config = GameConfig(
        game_name=title.split("—")[0].strip() if "—" in title else title,
        gdd_path=gdd_path,
        game_type=game_type,
        description=title,
        target_platforms=platforms,
        game_framework=framework,
        art_style=art_style,
        output_dir="./output",
    )
    
    milestones = [
        Milestone(
            id="1",
            title="Core Game Loop",
            description="Minimum playable version: basic game round from start to scoring",
            prerequisites=[],
            next=["2"],
            programming_language=language,
            agents=[
                AgentConfig(role=AgentRole.DESIGNER, temperature=0.7, system_prompt="Design data structures, game rules, and core mechanics"),
                AgentConfig(role=AgentRole.CODER, temperature=0.3, system_prompt="Implement the game logic from design specs"),
                AgentConfig(role=AgentRole.PLAYTESTER, temperature=0.0, system_prompt="Run game simulations and report statistics"),
                AgentConfig(role=AgentRole.CRITIC, temperature=0.3, system_prompt="Review designs, code, and playtest results for correctness"),
            ],
            speaker_order=[AgentRole.DESIGNER, AgentRole.CRITIC, AgentRole.CODER, AgentRole.CRITIC, AgentRole.PLAYTESTER, AgentRole.CRITIC],
            max_rounds=20,
            playtest_criteria=[
                PlaytestCriteria(
                    description="Can complete a basic game round from deal to scoring",
                    metric="completion_rate",
                    threshold=1.0,
                ),
            ],
        ),
        Milestone(
            id="2",
            title="Roguelike Structure",
            description="Add progression: antes, blinds, shops, and god tiles",
            prerequisites=["1"],
            next=["3"],
            programming_language=language,
            agents=[
                AgentConfig(role=AgentRole.DESIGNER, temperature=0.7, system_prompt="Design progression systems: antes, shops, god tiles"),
                AgentConfig(role=AgentRole.CODER, temperature=0.3, system_prompt="Implement progression and economy systems"),
                AgentConfig(role=AgentRole.PLAYTESTER, temperature=0.0, system_prompt="Run full-run simulations through all 8 antes"),
                AgentConfig(role=AgentRole.CRITIC, temperature=0.3, system_prompt="Ensure progression systems are balanced and complete"),
            ],
            speaker_order=[AgentRole.DESIGNER, AgentRole.CRITIC, AgentRole.CODER, AgentRole.CRITIC, AgentRole.PLAYTESTER, AgentRole.CRITIC],
            max_rounds=20,
            playtest_criteria=[
                PlaytestCriteria(
                    description="Can play through all 8 antes",
                    metric="full_run_completion",
                    threshold=0.8,
                ),
            ],
        ),
        Milestone(
            id="3",
            title="Balance and Polish",
            description="Tune difficulty, balance god tiles, ensure viable strategies",
            prerequisites=["2"],
            next=[],
            programming_language=language,
            agents=[
                AgentConfig(role=AgentRole.PLAYTESTER, temperature=0.0, system_prompt="Run 1000-game simulations and report detailed statistics"),
                AgentConfig(role=AgentRole.BALANCER, temperature=0.5, system_prompt="Analyze playtest data and propose balance adjustments"),
                AgentConfig(role=AgentRole.CODER, temperature=0.3, system_prompt="Apply balance parameter changes to game code"),
                AgentConfig(role=AgentRole.CRITIC, temperature=0.3, system_prompt="Validate that balance changes improve overall game health"),
            ],
            speaker_order=[AgentRole.PLAYTESTER, AgentRole.BALANCER, AgentRole.CRITIC, AgentRole.CODER, AgentRole.PLAYTESTER, AgentRole.CRITIC],
            max_rounds=15,
            playtest_criteria=[
                PlaytestCriteria(
                    description="Early ante win rate 65-80%",
                    metric="ante_1_2_win_rate",
                    threshold=0.65,
                    operator=">=",
                ),
                PlaytestCriteria(
                    description="No single god tile >90% purchase rate",
                    metric="max_god_tile_purchase_rate",
                    threshold=0.9,
                    operator="<",
                ),
            ],
        ),
    ]
    
    plan = ExecutionPlan(game=game_config, milestones=milestones)
    
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))
        print(f"Plan saved to: {output_path}")
    
    return plan
