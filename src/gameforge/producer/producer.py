"""Producer — reads a GDD and generates an ExecutionPlan JSON.

The Producer calls an LLM to:
1. Extract game metadata (GameConfig)
2. Break the game into ordered Milestones
3. Break each Milestone into Tasks with agent assignments
4. Define playtest criteria per milestone

Output: a validated ExecutionPlan (Pydantic model) that can be serialized to JSON.
"""

import json
from pathlib import Path

from gameforge.models.plan import (
    AgentConfig,
    AgentRole,
    ExecutionPlan,
    GameConfig,
    Milestone,
    PlaytestCriteria,
    Task,
    TaskStatus,
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
      "programming_language": "typescript",
      "tasks": [
        {{
          "id": "1.1",
          "title": "string",
          "description": "detailed task spec",
          "depends_on": ["1.0"],
          "agents": [
            {{
              "role": "designer",
              "temperature": 0.7,
              "max_rounds": 15,
              "system_prompt": "specific instructions for this task"
            }}
          ],
          "max_iterations": 5
        }}
      ],
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
2. **Each milestone adds ONE major system** — don't cram too much in
3. **Tasks should be small** — 1-2 hours of agent work each
4. **Dependencies matter** — task 1.3 can't start before 1.1 and 1.2
5. **Every task gets agents** — at minimum Designer + Critic, or Coder + Critic
6. **Playtest criteria are measurable** — "can complete a round", "win rate > 40%"
7. **System prompts are task-specific** — reference the actual game mechanics

### Agent Roles:
- **designer**: designs mechanics, data structures, rules
- **critic**: reviews all proposals, finds edge cases
- **coder**: writes code from design specs
- **balancer**: analyzes playtest data, proposes adjustments
- **playtester**: runs simulations (algorithmic, not LLM)

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
    """Generate an ExecutionPlan by calling an LLM.
    
    Args:
        gdd_content: The raw GDD markdown text
        gdd_path: Path to the GDD file
        llm_fn: A callable(prompt: str) -> str that calls the LLM.
                 If None, uses a default implementation.
    
    Returns:
        A validated ExecutionPlan
    """
    prompt = PLAN_GENERATION_PROMPT.format(gdd_content=gdd_content)
    
    if llm_fn is None:
        # Default: try ollama local, then fall back to placeholder
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
    
    # Parse the LLM output
    plan_data = json.loads(raw_json)
    
    # Add gdd_path to game config
    if "game" in plan_data:
        plan_data["game"]["gdd_path"] = gdd_path
    
    # Validate with Pydantic
    plan = ExecutionPlan.model_validate(plan_data)
    
    return plan


def produce(gdd_path: str, llm_fn=None, output_path: str | None = None) -> ExecutionPlan:
    """Main entry point: read GDD → generate plan → optionally save.
    
    Args:
        gdd_path: Path to the GDD markdown file
        llm_fn: Optional custom LLM callable
        output_path: If provided, save the plan JSON here
    
    Returns:
        The generated ExecutionPlan
    """
    # Read GDD
    gdd_content = read_gdd(gdd_path)
    
    # Generate plan
    plan = generate_plan_with_llm(gdd_content, gdd_path, llm_fn)
    
    # Save if requested
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
    """Full pipeline: normalize GDD → generate milestones → save all files.
    
    Output:
        - output_dir/gdd_normalized.md (system prompt for agents)
        - output_dir/milestone_1_*.json (one per milestone)
    
    Args:
        gdd_path: Path to user's raw GDD
        output_dir: Where to save all output files
        llm_fn: Optional LLM callable
    
    Returns:
        Tuple of (normalized_gdd_path, list_of_milestone_paths)
    """
    from gameforge.producer.normalizer import normalize_gdd
    
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Read and normalize GDD
    gdd_content = read_gdd(gdd_path)
    gdd_normalized_path = str(out / "gdd_normalized.md")
    normalize_gdd(gdd_content, output_path=gdd_normalized_path, llm_fn=llm_fn)
    
    # Step 2: Generate plan (template or LLM)
    if llm_fn:
        plan = generate_plan_with_llm(gdd_content, gdd_path, llm_fn)
    else:
        plan = produce_from_template(gdd_path)
    
    # Step 3: Save each milestone as separate JSON
    milestone_paths = plan.save_milestones(output_dir)
    
    # Step 4: Also save overview (for reference, not execution)
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
    Reads the GDD and creates a reasonable default plan.
    """
    gdd_content = read_gdd(gdd_path)
    
    # Extract basic info from GDD
    lines = gdd_content.split("\n")
    title = lines[0].replace("#", "").strip() if lines else "Unknown Game"
    
    # Detect framework from GDD
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
        language = "python"
    
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
    
    # Create default milestones
    milestones = [
        Milestone(
            id="1",
            title="Core Game Loop",
            description="Minimum playable version: basic game round from start to scoring",
            programming_language=language,
            tasks=[
                Task(
                    id="1.1",
                    title="Data structures and types",
                    description="Define all core data types: tiles, hands, melds, scoring",
                    agents=[
                        AgentConfig(role=AgentRole.DESIGNER, temperature=0.7, max_rounds=15),
                        AgentConfig(role=AgentRole.CRITIC, temperature=0.3, max_rounds=10),
                    ],
                ),
                Task(
                    id="1.2",
                    title="Core game logic",
                    description="Implement the main game loop: draw, discard, meld, win detection",
                    depends_on=["1.1"],
                    agents=[
                        AgentConfig(role=AgentRole.CODER, temperature=0.3, max_rounds=20),
                        AgentConfig(role=AgentRole.CRITIC, temperature=0.3, max_rounds=10),
                    ],
                ),
                Task(
                    id="1.3",
                    title="Scoring system",
                    description="Implement scoring: base score, fan patterns, multipliers",
                    depends_on=["1.1", "1.2"],
                    agents=[
                        AgentConfig(role=AgentRole.DESIGNER, temperature=0.7, max_rounds=15),
                        AgentConfig(role=AgentRole.CODER, temperature=0.3, max_rounds=20),
                        AgentConfig(role=AgentRole.CRITIC, temperature=0.3, max_rounds=10),
                    ],
                ),
            ],
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
            programming_language=language,
            tasks=[
                Task(
                    id="2.1",
                    title="Ante and blind system",
                    description="Implement 8 antes with 3 blinds each, scaling targets",
                    agents=[
                        AgentConfig(role=AgentRole.DESIGNER, temperature=0.7),
                        AgentConfig(role=AgentRole.CODER, temperature=0.3),
                        AgentConfig(role=AgentRole.CRITIC, temperature=0.3),
                    ],
                ),
                Task(
                    id="2.2",
                    title="Shop and economy",
                    description="Implement shop phase: buying god tiles, flower cards, gold management",
                    depends_on=["2.1"],
                    agents=[
                        AgentConfig(role=AgentRole.DESIGNER, temperature=0.7),
                        AgentConfig(role=AgentRole.CODER, temperature=0.3),
                        AgentConfig(role=AgentRole.CRITIC, temperature=0.3),
                    ],
                ),
                Task(
                    id="2.3",
                    title="God tiles and flower cards",
                    description="Implement passive abilities (god tiles) and consumables (flower cards)",
                    depends_on=["2.1"],
                    agents=[
                        AgentConfig(role=AgentRole.DESIGNER, temperature=0.7),
                        AgentConfig(role=AgentRole.CODER, temperature=0.3),
                        AgentConfig(role=AgentRole.CRITIC, temperature=0.3),
                    ],
                ),
            ],
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
            programming_language=language,
            tasks=[
                Task(
                    id="3.1",
                    title="Difficulty tuning",
                    description="Adjust score targets, shop prices, god tile effects for target win rates",
                    agents=[
                        AgentConfig(role=AgentRole.BALANCER, temperature=0.5),
                        AgentConfig(role=AgentRole.CRITIC, temperature=0.3),
                    ],
                ),
                Task(
                    id="3.2",
                    title="Strategy viability check",
                    description="Ensure 4+ viable build strategies through mass simulation",
                    depends_on=["3.1"],
                    agents=[
                        AgentConfig(role=AgentRole.BALANCER, temperature=0.5),
                        AgentConfig(role=AgentRole.CRITIC, temperature=0.3),
                    ],
                ),
            ],
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
    
    plan = ExecutionPlan(
        game=game_config,
        milestones=milestones,
    )
    
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))
        print(f"Plan saved to: {output_path}")
    
    return plan
