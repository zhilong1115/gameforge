"""GDD Normalizer — standardizes and completes a user's Game Design Document.

Part of the Producer pipeline:
1. Read user's raw GDD (any format)
2. Check for required/missing sections
3. Generate missing content (milestones, data structures, tech architecture)
4. Output a standardized GDD.md for user review
5. User edits → feeds into Producer for JSON generation

Required sections (user MUST provide):
  - Game Name
  - Game Type
  - Core Mechanics
  - Win/Lose Condition
  - Target Platform
  - Tech Stack (language + framework)

Generated sections (we fill if missing):
  - Milestone Breakdown
  - Data Structure Design
  - Technical Architecture
  - Agent Assignment Recommendations
  - Balance Targets
  - Art Style (if not specified)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GDDSection:
    """A section of the GDD with its content and status."""
    name: str
    required: bool
    content: str = ""
    present: bool = False
    generated: bool = False


@dataclass
class GDDAnalysis:
    """Result of analyzing a raw GDD."""
    sections: dict[str, GDDSection] = field(default_factory=dict)
    raw_content: str = ""
    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if all required sections are present."""
        return len(self.missing_required) == 0


# Section definitions
REQUIRED_SECTIONS = {
    "game_name": "Game Name",
    "game_type": "Game Type / Genre",
    "core_mechanics": "Core Mechanics",
    "win_lose": "Win/Lose Condition",
    "target_platform": "Target Platform",
    "tech_stack": "Tech Stack (language + framework)",
}

OPTIONAL_SECTIONS = {
    "scoring": "Scoring / Economy System",
    "progression": "Progression Structure",
    "balance_targets": "Balance Targets",
    "art_style": "Art Style",
    "milestones": "Milestone Breakdown",
    "data_structures": "Data Structure Design",
    "tech_architecture": "Technical Architecture",
    "agent_config": "Agent Assignment Recommendations",
}

# Keywords to detect section presence
SECTION_KEYWORDS = {
    "game_name": [r"^#\s+\w+"],  # First H1 header
    "game_type": ["roguelike", "rpg", "platformer", "puzzle", "deck.?builder",
                   "strategy", "simulation", "shooter", "racing", "genre"],
    "core_mechanics": ["mechanic", "gameplay", "core.?loop", "how.*play",
                       "rules", "tiles", "cards", "combat", "movement"],
    "win_lose": ["win", "lose", "victory", "defeat", "game.?over",
                  "score.?target", "objective", "goal"],
    "target_platform": ["platform", "web", "mobile", "desktop", "html5",
                         "youtube.*playable", "steam", "ios", "android"],
    "tech_stack": ["phaser", "godot", "unity", "unreal", "pygame",
                    "typescript", "javascript", "python", "gdscript", "c#",
                    "vite", "webpack", "engine"],
    "scoring": ["score", "scoring", "point", "gold", "currency", "economy",
                "reward", "multiplier"],
    "progression": ["ante", "level", "stage", "round", "wave", "chapter",
                     "progression", "difficulty", "blind"],
    "balance_targets": ["balance", "win.?rate", "difficulty.?curve",
                         "viable.?strateg"],
    "art_style": ["pixel", "art.?style", "2d", "3d", "cartoon", "ascii",
                   "sprite", "visual"],
    "milestones": ["milestone", "phase", "sprint", "mvp", "minimum.?viable"],
    "data_structures": ["data.?struct", "class", "type", "interface", "schema",
                         "model"],
    "tech_architecture": ["architect", "module", "component", "layer",
                           "pipeline", "system.?design"],
    "agent_config": ["agent", "designer", "coder", "critic", "balancer"],
}


def analyze_gdd(gdd_content: str) -> GDDAnalysis:
    """Analyze a raw GDD and identify present/missing sections.

    Args:
        gdd_content: Raw markdown content of the GDD

    Returns:
        GDDAnalysis with section status and missing items
    """
    analysis = GDDAnalysis(raw_content=gdd_content)
    content_lower = gdd_content.lower()

    # Check each section
    for key, label in {**REQUIRED_SECTIONS, **OPTIONAL_SECTIONS}.items():
        is_required = key in REQUIRED_SECTIONS
        keywords = SECTION_KEYWORDS.get(key, [])

        present = False
        for kw in keywords:
            if re.search(kw, content_lower):
                present = True
                break

        section = GDDSection(
            name=label,
            required=is_required,
            present=present,
        )
        analysis.sections[key] = section

        if not present:
            if is_required:
                analysis.missing_required.append(label)
            else:
                analysis.missing_optional.append(label)

    return analysis


# ── LLM Prompt for GDD Normalization ──

NORMALIZE_PROMPT = """You are a game development expert. A user has provided a Game Design Document (GDD).
Your job is to create a STANDARDIZED version that includes ALL necessary sections.

IMPORTANT: Keep all of the user's original content. Only ADD missing sections.

The standardized GDD must follow this format:

```markdown
# [Game Name]

## Metadata
- **Type**: [genre(s)]
- **Platform**: [target platforms]
- **Framework**: [game engine/framework]
- **Language**: [programming language]
- **Art Style**: [visual style]

## Core Mechanics
[User's content, keep as-is]

## Win/Lose Conditions
[User's content or generate if missing]

## Scoring / Economy
[User's content or generate if missing]

## Progression Structure
[User's content or generate if missing]

## Milestones (Review and edit these)
### Milestone 1: [Title]
- **Goal**: [What this milestone achieves]
- **Tasks**:
  - Task 1.1: [title] — Agents: [designer + critic]
  - Task 1.2: [title] — Agents: [coder + critic]
- **Playtest Criteria**: [measurable pass condition]

### Milestone 2: [Title]
...

## Data Structure Design
[Key classes/types needed, with fields]

## Technical Architecture
[High-level module layout]

## Balance Targets
[Specific measurable goals]

## Agent Configuration (Review and edit)
- **Default Model**: claude-sonnet-4-6
- **LLM Config**: ./llm_config.json
- **Custom Skills Directory**: ./skills/ (optional)
```

Missing sections that need to be GENERATED: {missing_sections}

---

USER'S ORIGINAL GDD:

{gdd_content}

---

Output the COMPLETE standardized GDD in markdown format. Keep all user content, add missing sections."""


def normalize_gdd(
    gdd_content: str,
    output_path: str | None = None,
    llm_fn=None,
) -> str:
    """Normalize a raw GDD into standardized format.

    Args:
        gdd_content: Raw GDD markdown
        output_path: If provided, save normalized GDD here
        llm_fn: Optional LLM callable for generating missing sections.
                If None, uses template-based generation.

    Returns:
        Standardized GDD markdown string
    """
    # Analyze what's missing
    analysis = analyze_gdd(gdd_content)

    all_missing = analysis.missing_required + analysis.missing_optional

    if not all_missing:
        # GDD is already complete
        normalized = gdd_content
    elif llm_fn is not None:
        # Use LLM to generate missing sections
        prompt = NORMALIZE_PROMPT.format(
            missing_sections=", ".join(all_missing),
            gdd_content=gdd_content,
        )
        normalized = llm_fn(prompt)
    else:
        # Template-based: just append section headers for missing parts
        normalized = gdd_content + "\n\n"
        normalized += "---\n\n"
        normalized += "## Generated Sections (Please review and edit)\n\n"

        for section_name in all_missing:
            normalized += f"### {section_name}\n"
            normalized += f"<!-- TODO: Fill in {section_name} -->\n\n"

    # Save if requested
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(normalized)
        print(f"Normalized GDD saved to: {output_path}")

    return normalized


def print_analysis(analysis: GDDAnalysis) -> None:
    """Print a summary of the GDD analysis."""
    print("GDD Analysis:")
    print(f"  Valid: {'✅' if analysis.is_valid else '❌'}")
    print()

    print("  Present sections:")
    for key, section in analysis.sections.items():
        if section.present:
            marker = "✅" if section.required else "📝"
            print(f"    {marker} {section.name}")

    if analysis.missing_required:
        print()
        print("  ❌ Missing REQUIRED:")
        for name in analysis.missing_required:
            print(f"    - {name}")

    if analysis.missing_optional:
        print()
        print("  ⚠️ Missing (will generate):")
        for name in analysis.missing_optional:
            print(f"    - {name}")
