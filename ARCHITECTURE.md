# GameForge — Architecture & Design Document

**AI-Powered Game Development Studio**

| | |
|---|---|
| **Author** | Zhilong Zheng |
| **Last Updated** | 2026-03-22 |
| **Status** | In Development |
| **Repository** | [github.com/zhilong1115/gameforge](https://github.com/zhilong1115/gameforge) |

---

## 1. Overview

### 1.1 Problem Statement

Building a game from a design document requires coordinating multiple disciplines — game design, programming, playtesting, and balancing. Each discipline involves iterative feedback loops: design something, code it, test it, find problems, redesign. This is slow, expensive, and difficult to parallelize with human teams.

### 1.2 Solution

GameForge is a multi-agent AI system that takes a **Game Design Document (GDD)** as input and produces a **playable, balanced game** as output. It uses specialized AI agents (Designer, Coder, Critic, Balancer) orchestrated by a DAG-based workflow engine, with human review at milestone checkpoints.

### 1.3 Key Design Principles

1. **GDD is human input** — GameForge builds games, it doesn't invent them
2. **Milestone-based iteration** — each milestone produces a playable artifact
3. **DAG orchestration** — milestones can run in parallel when dependencies allow
4. **Human-in-the-loop** — human reviews at milestone boundaries, not per-task
5. **Separation of concerns** — LangGraph for flow control, AutoGen for agent collaboration

### 1.4 Input / Output

```
Input:  game_design.md (human-written GDD)
Output: Playable game with balanced mechanics + test suite
```

### 1.5 User Configuration

GameForge requires two things from the user:

#### Game Design Document (GDD)
A markdown file describing the game. Can be rough — the Normalizer fills in gaps. Minimum viable GDD needs: game name, core mechanic, and target platform.

#### LLM API Configuration (`llm_config.json`)
Specifies which LLM providers and models to use for each agent role:

```json
{
  "default": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "api_key": "${ANTHROPIC_API_KEY}",
    "temperature": 0.7
  },
  "fast": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_key": "${OPENAI_API_KEY}",
    "temperature": 0.3
  },
  "local": {
    "provider": "ollama",
    "model": "qwen2.5:7b",
    "base_url": "http://localhost:11434",
    "temperature": 0.7
  }
}
```

Each `AgentConfig` references a key from this file (e.g. `model: "default"` or `model: "fast"`). This decouples agent logic from LLM provider — swap models without changing the plan.

The `ExecutionPlan` stores the config path:
```python
class ExecutionPlan(BaseModel):
    llm_config_path: str = "./llm_config.json"
    custom_skills_dir: str | None = None  # optional user-provided tools
```

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      GameForge                           │
│                                                          │
│  ┌──────────┐    ┌────────────────────────────────────┐ │
│  │ Producer  │───→│         Milestone DAG               │ │
│  │ (Planning)│    │                                    │ │
│  └──────────┘    │  ┌───┐     ┌───┐     ┌───┐        │ │
│                   │  │ 1 │────→│ 2 │     │ 3 │        │ │
│                   │  └───┘────→└───┘────→└───┘        │ │
│                   │            │ 3 │────→│   │        │ │
│                   │            └───┘     └───┘        │ │
│                   └──────────────┬─────────────────────┘ │
│                                  │                        │
│               ┌──────────────────┼──────────────────┐    │
│               │    Per-Milestone Execution           │    │
│               │                                      │    │
│               │  Design → Code → Playtest → Balance  │    │
│               │     ↑                          │     │    │
│               │     └──── retry if failed ─────┘     │    │
│               │                                      │    │
│               └──────────────────┬───────────────────┘    │
│                                  │                        │
│                          🧑 Human Review                  │
│                        (approve / reject)                 │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Framework Responsibilities

| Framework | Role | Analogy |
|-----------|------|---------|
| **LangGraph** | Orchestration — manages milestone DAG, state transitions, human checkpoints | Project Manager |
| **AutoGen** | Collaboration — multi-agent discussions within tasks (design, code review, balancing) | Team Meetings |

**Why two frameworks?** LangGraph excels at deterministic workflows with state management and checkpointing. AutoGen excels at free-form multi-agent conversation. GameForge uses each where it's strongest.

---

## 3. Detailed Design

### 3.1 Data Models

All data flows through Pydantic models for type safety and serialization.

#### 3.1.1 Core Models

```
ExecutionPlan
├── GameConfig              — game metadata (name, framework, platforms, art style)
├── llm_config_path         — path to LLM API credentials
└── Milestone[]             — DAG of development milestones
    ├── prerequisites[]     — milestone IDs that must complete first
    ├── next[]              — milestone IDs unlocked on completion
    ├── status              — PENDING → READY → IN_PROGRESS → DONE / FAILED
    ├── agents[]            — AutoGen agents in this GroupChat
    │   ├── role            — designer / critic / coder / balancer
    │   ├── model           — references key in llm_config.json
    │   ├── temperature     — LLM temperature
    │   └── system_prompt   — task-specific instructions
    ├── speaker_order[]     — agent speaking sequence (e.g. [designer, critic, coder, critic])
    ├── manager_model       — LLM config key for GroupChatManager
    ├── max_rounds          — max conversation rounds
    ├── max_iterations      — max retry cycles (design→code→test)
    └── PlaytestCriteria[]  — measurable pass/fail conditions
```

Each Milestone is the **atomic execution unit** — there is no Task layer. If a milestone feels too big, break it into smaller milestones in the DAG instead of nesting tasks. This keeps the model flat and maps 1:1 to AutoGen GroupChat sessions.

#### 3.1.2 Milestone Lifecycle

```
PENDING ──→ READY ──→ IN_PROGRESS ──→ DONE
  │           │                        │
  │           │ (prerequisites met)    │ (playtest passed + human approved)
  │           │                        │
  │           └──→ IN_PROGRESS ──→ FAILED
  │                    │
  │                    └──→ (retry → back to IN_PROGRESS)
  │
  └──→ (waiting for prerequisites)
```

- **PENDING**: waiting for prerequisite milestones to complete
- **READY**: all prerequisites met, can be picked up for execution
- **IN_PROGRESS**: agents are actively working on tasks
- **DONE**: playtest passed and human approved
- **FAILED**: playtest failed after max retries, needs human intervention

#### 3.1.3 DAG Validation

The system validates the milestone DAG at plan creation:
1. **Reference check** — all prerequisite/next IDs must exist
2. **Mirror consistency** — if A.next contains B, then B.prerequisites must contain A
3. **Cycle detection** — topological sort (Kahn's algorithm) to ensure no circular dependencies

#### 3.1.4 Milestone Config (JSON)

Each milestone is saved as a self-contained JSON file that doubles as an AutoGen GroupChat configuration. Example `milestone_1_core_game_loop.json`:

```json
{
  "id": "1",
  "title": "Core Game Loop",
  "description": "Minimum playable version: basic game round from start to scoring",
  "prerequisites": [],
  "next": ["2", "3"],
  "programming_language": "typescript",
  "agents": [
    {
      "role": "designer",
      "model": "default",
      "temperature": 0.7,
      "system_prompt": "Design data structures, game rules, and core mechanics for a mahjong game"
    },
    {
      "role": "coder",
      "model": "default",
      "temperature": 0.3,
      "system_prompt": "Implement the game logic from design specs in TypeScript"
    },
    {
      "role": "critic",
      "model": "fast",
      "temperature": 0.3,
      "system_prompt": "Review designs and code for correctness, edge cases, and completeness"
    }
  ],
  "speaker_order": ["designer", "critic", "coder", "critic"],
  "manager_model": "default",
  "max_rounds": 20,
  "max_iterations": 5,
  "iterations": 0,
  "playtest_criteria": [
    {
      "description": "Can complete a basic game round from deal to scoring",
      "metric": "completion_rate",
      "threshold": 1.0,
      "operator": ">="
    }
  ],
  "status": "pending",
  "human_approved": null,
  "human_feedback": ""
}
```

Key fields explained:

| Field | Purpose |
|-------|---------|
| `prerequisites` / `next` | DAG edges — defines execution order and parallelism |
| `agents` | AutoGen agents in this GroupChat; each references an LLM config key via `model` |
| `agents[].system_prompt` | Milestone-specific instructions injected into the agent's prompt |
| `speaker_order` | Defines the AutoGen conversation flow (who speaks in what order) |
| `manager_model` | LLM config key for the AutoGen GroupChatManager (decides speaker transitions) |
| `max_rounds` | Max conversation rounds in the GroupChat — controls cost |
| `max_iterations` | Max design→code→test retry cycles before escalating to human |
| `playtest_criteria` | Measurable conditions that must pass for the milestone to complete |
| `human_approved` | `null` = not reviewed, `true` = approved, `false` = rejected |
| `human_feedback` | Human's notes when rejecting — fed back to agents on retry |

### 3.2 Producer (Planning Phase)

The Producer reads the GDD and generates a structured execution plan.

```
GDD (markdown) ──→ Normalizer ──→ Normalized GDD (system prompt)
                ──→ Planner   ──→ Milestone DAG (JSON files)
```

#### 3.2.1 GDD Normalizer

Ensures the GDD has all required sections:
- Game Overview, Core Mechanics, Progression, Technical Requirements
- Fills gaps with sensible defaults
- Output: `gdd_normalized.md` — shared system prompt for all agents

#### 3.2.2 Milestone Planner

Breaks the game into ordered milestones:
- **Rule 1**: Milestone 1 is always the minimum playable version
- **Rule 2**: Each milestone adds ONE major system
- **Rule 3**: Tasks within a milestone are 1-2 hours of agent work
- **Rule 4**: Every task has measurable playtest criteria
- **Rule 5**: Dependencies form a valid DAG (supports parallel execution)

Output: One JSON file per milestone, each directly usable as AutoGen GroupChat config.

### 3.3 Orchestrator (Execution Phase)

The LangGraph orchestrator manages the milestone DAG execution.

#### 3.3.1 State Management

```python
class GameForgeState(TypedDict):
    # GDD
    gdd_content: str
    game_name: str
    
    # Plan — milestone status tracked on Milestone.status directly
    execution_plan: dict            # Serialized ExecutionPlan
    current_milestone_id: str | None  # ID of milestone being executed
    
    # Phase outputs
    design_spec: dict | None   # Current design proposal
    generated_files: dict      # filename → code
    generated_tests: dict      # test filename → code
    playtest_results: dict     # Simulation results
    balance_adjustments: list  # Proposed tweaks
    
    # Control
    phase: str                 # design | code | playtest | balance | human_review
    iteration_count: int
    max_iterations: int
    
    # Human
    human_approved: bool | None
    human_feedback: str
```

Key design decision: **Milestone status lives on the Milestone model itself**, not duplicated in LangGraph state. `ExecutionPlan.ready_milestones()` computes what can run next by checking prerequisites against each milestone's status.

#### 3.3.2 Execution Flow

```
1. Load ExecutionPlan
2. Call plan.ready_milestones() → get READY milestones
3. For each READY milestone (can parallelize):
   a. Set status = IN_PROGRESS
   b. Execute tasks in dependency order:
      - Design phase (AutoGen: Designer + Critic)
      - Code phase (AutoGen: Coder + Critic)
      - Playtest phase (Algorithmic simulator)
      - Balance phase (AutoGen: Balancer + Critic)
   c. If playtest fails and iterations < max: retry from (b)
   d. If playtest passes: human review checkpoint
   e. Human approves → status = DONE
   f. Human rejects → incorporate feedback, retry
4. Repeat from (2) until plan.is_complete
```

### 3.4 Agents

Five specialized agents, each with a focused role:

| Agent | Type | Role | Key Behaviors |
|-------|------|------|---------------|
| **Producer** | LangGraph node | Plans milestones from GDD | Reads GDD, outputs DAG, assigns agents to tasks |
| **Designer** | AutoGen participant | Designs mechanics & data structures | Proposes solutions, iterates with Critic, outputs design specs |
| **Critic** | AutoGen participant | Quality gate for all phases | Challenges assumptions, finds edge cases, must approve before proceeding |
| **Coder** | AutoGen participant | Generates code from design specs | Writes implementation + tests, responds to Critic review feedback |
| **Balancer** | AutoGen participant | Tunes game numbers | Analyzes playtest statistics, proposes parameter adjustments |

The **Playtester** is not an LLM agent — it's an algorithmic simulator that runs the game engine with heuristic strategies and collects statistics.

### 3.5 Simulator (Playtesting)

**Design decision**: The playtester is algorithmic, not LLM-based.

- **Why**: Running GPT to play 1000 games of mahjong would cost hundreds of dollars and take hours. Greedy heuristic strategies run in seconds.
- **How**: `game_engine.py` implements the game rules. `strategies.py` provides greedy/random AI players. `runner.py` orchestrates N simulations and collects metrics.
- **Output**: `PlaytestResult` with metrics like win rate, score distribution, strategy dominance percentages.

### 3.6 Translator

Converts the abstract execution plan into framework-specific configurations:
- Maps `AgentConfig` → AutoGen `AssistantAgent` with system prompts
- Configures `GroupChat` with the right agents per task
- Injects the normalized GDD as shared context

---

## 4. Data Flow

```
                    ┌─────────────────────────────┐
                    │       game_design.md          │
                    │       (Human Input)           │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │        Producer               │
                    │  Normalize GDD + Plan DAG     │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┼────────────────────┐
              │                │                     │
     ┌────────▼──────┐ ┌──────▼───────┐ ┌──────────▼─────┐
     │ gdd_norm.md   │ │ milestone_1  │ │ milestone_N    │
     │ (system prompt)│ │   .json      │ │   .json        │
     └───────────────┘ └──────┬───────┘ └────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │     Orchestrator (LangGraph)  │
                    │     Execute milestone DAG     │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                 │
     ┌────────▼──────┐ ┌──────▼─────┐ ┌────────▼──────┐
     │ Design Phase  │ │ Code Phase │ │ Balance Phase │
     │ (AutoGen)     │ │ (AutoGen)  │ │ (AutoGen)     │
     └───────────────┘ └──────┬─────┘ └───────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │     Playtest (Simulator)      │
                    │     N games → statistics      │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │     🧑 Human Checkpoint       │
                    │     Approve / Reject / Adjust │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │     Output: Playable Game 🎮  │
                    │     + Test Suite              │
                    └──────────────────────────────┘
```

---

## 5. Project Structure

```
gameforge/
├── src/gameforge/
│   ├── __init__.py
│   ├── cli.py                  # CLI: gf producer, gf run
│   ├── models/
│   │   ├── plan.py             # ExecutionPlan, Milestone, Task, GameConfig
│   │   └── design.py           # DesignSpec, CodeOutput, PlaytestResult, BalanceAdjustment
│   ├── producer/
│   │   ├── producer.py         # GDD → milestone DAG (LLM or template)
│   │   └── normalizer.py       # GDD → normalized system prompt
│   ├── agents/
│   │   ├── __init__.py         # Agent registry + system prompts
│   │   ├── designer.py         # Game mechanics & data structure design
│   │   ├── critic.py           # Quality review for all phases
│   │   ├── coder.py            # Code generation from design specs
│   │   ├── balancer.py         # Playtest analysis & parameter tuning
│   │   └── producer.py         # Planning agent system prompt
│   ├── orchestrator/
│   │   ├── graph.py            # LangGraph DAG workflow definition
│   │   └── state.py            # GameForgeState (TypedDict)
│   ├── simulator/              # Algorithmic playtesting (no LLM)
│   ├── translator/             # Plan → AutoGen GroupChat config
│   ├── eval/                   # Metrics collection & reporting
│   └── tools/                  # LLM client & file I/O utilities
├── tests/
│   ├── test_models.py          # 21 tests: data models, DAG validation
│   └── test_producer.py        # 9 tests: GDD parsing, normalization, planning
├── examples/
│   └── hu/                     # HU — Roguelike Mahjong (reference GDD)
├── ARCHITECTURE.md             # This document
├── README.md
└── pyproject.toml
```

---

## 6. Key Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **LangGraph + AutoGen hybrid** | LangGraph for deterministic flow + state; AutoGen for free-form agent collaboration |
| 2 | **DAG-based milestones** (not linear) | Enables parallel execution; mirrors real game dev where UI and audio don't block each other |
| 3 | **Milestone status on the model** | Single source of truth; no state duplication between LangGraph state and plan |
| 4 | **READY state in lifecycle** | Explicit readiness signal; orchestrator doesn't need to recompute prerequisites |
| 5 | **Algorithmic playtester** | LLM-based testing is too slow/expensive; heuristic strategies give reliable statistics |
| 6 | **Separate milestone JSONs** | Each milestone is a self-contained AutoGen config; can be run/tested independently |
| 7 | **Human-in-the-loop at milestones** | Practical engineering — full autonomy is risky; milestone reviews catch issues early |
| 8 | **GDD normalization** | Ensures consistent structure regardless of how the human wrote the GDD |
| 9 | **DAG validation at plan time** | Catches broken dependencies, missing references, and cycles before execution |
| 10 | **prerequisites + next (bidirectional)** | Readable from either side; easy to validate mirror consistency |

---

## 7. Example: HU — Roguelike Mahjong Deck-Builder

The reference implementation uses HU, a Balatro-inspired mahjong roguelike.

### Milestone DAG

```
┌─────────────────────┐
│ M1: Core Mahjong    │ (tiles, draw, discard, win detection)
│ prerequisites: []   │
│ next: [2, 3]        │
└──────┬──────────────┘
       │
       ├──────────────────────────┐
       │                          │
┌──────▼──────────────┐  ┌───────▼─────────────┐
│ M2: Roguelike Layer │  │ M3: UI & Rendering  │  ← parallel
│ (antes, shops, gods)│  │ (Phaser 3, mobile)  │
│ prerequisites: [1]  │  │ prerequisites: [1]  │
│ next: [4]           │  │ next: [4]           │
└──────┬──────────────┘  └───────┬─────────────┘
       │                          │
       └──────────┬───────────────┘
                  │
       ┌──────────▼──────────────┐
       │ M4: Balance & Polish    │  ← fan-in (waits for M2 AND M3)
       │ (1000-game simulation)  │
       │ prerequisites: [2, 3]   │
       │ next: []                │
       └─────────────────────────┘
```

### Playtest Criteria Examples

| Milestone | Criteria | Metric | Threshold |
|-----------|----------|--------|-----------|
| M1 | Can complete a basic round | completion_rate | = 100% |
| M2 | Can play through all 8 antes | full_run_completion | ≥ 80% |
| M4 | Early ante win rate healthy | ante_1_2_win_rate | 65-80% |
| M4 | No dominant god tile | max_god_tile_purchase_rate | < 90% |

---

## 8. Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Orchestration | LangGraph (Python) | State management, checkpointing, human-in-the-loop |
| Agent Chat | AutoGen (Python) | Multi-agent GroupChat with natural conversation |
| LLM Backend | Claude / GPT-4 (API) | Strong coding + reasoning for agents |
| Data Models | Pydantic v2 | Type safety, serialization, validation |
| Game Engine | Python | Algorithmic simulation for playtesting |
| CLI | Click / argparse | `gf producer analyze`, `gf run` |
| Testing | pytest | 30 tests (models + producer) |
| Package | pyproject.toml (hatch) | Modern Python packaging |

---

## 9. Future Work

- [ ] **Orchestrator implementation** — wire up LangGraph DAG execution with `ready_milestones()`
- [ ] **AutoGen integration** — connect agent prompts to actual GroupChat sessions
- [ ] **Simulator** — game engine + heuristic strategies + statistics collection
- [ ] **Translator** — map milestone JSON → AutoGen GroupChat config
- [ ] **End-to-end demo** — run HU GDD through full pipeline
- [ ] **Multi-game support** — validate with different game types (platformer, RPG)
- [ ] **Checkpoint/resume** — pause and continue long-running builds
