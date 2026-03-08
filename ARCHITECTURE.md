# GameForge — Multi-Agent Game Content Generation System

**Status:** Phase 1 Architecture Design (Pending Review)
**Last Updated:** 2026-03-08
**Author:** HU Dev Agent
**Portfolio Target:** DeepMind Application

---

## Table of Contents

1. [Overview](#overview)
2. [HU Game Model](#hu-game-model)
3. [System Architecture](#system-architecture)
4. [Directory Structure](#directory-structure)
5. [Agent Interfaces](#agent-interfaces)
6. [Message & Data Formats](#message--data-formats)
7. [Agent Interaction Protocol](#agent-interaction-protocol)
8. [Tool Inventory](#tool-inventory)
9. [Evaluation Metrics](#evaluation-metrics)
10. [Boundaries (What GameForge Doesn't Own)](#boundaries)
11. [Open Questions for Review](#open-questions-for-review)

---

## Overview

**GameForge** is a multi-agent system that collaborates to automatically generate, stress-test, and balance content for HU — a roguelike mahjong deck-builder. Four specialized AI agents form a pipeline: one designs candidate content, one simulates thousands of game runs, one analyzes balance health, and one evaluates creative diversity.

The system is designed around clean agent boundaries, typed JSON message contracts, and a shared state store — making each agent independently testable, observable, and replaceable.

```
                    ┌─────────────────────────────────────────────┐
                    │              GameForge Orchestrator          │
                    └──────┬───────────────────────────┬──────────┘
                           │                           │
              ┌────────────▼───────────┐   ┌──────────▼──────────────┐
              │    Designer Agent      │   │     Critic Agent         │
              │  (LLM-driven)          │   │  (Diversity + Fun)       │
              │  Generates proposals   │   │  Scores the ecosystem    │
              └────────────┬───────────┘   └──────────▲──────────────┘
                           │                          │
              ┌────────────▼───────────┐   ┌──────────┴──────────────┐
              │   Simulator Agent      │──▶│    Balancer Agent        │
              │  (Rule Engine Wrapper) │   │  (Statistical Analysis)  │
              │  Runs 1000 games/batch │   │  Detects OP/UP content   │
              └────────────────────────┘   └─────────────────────────┘
                           │
              ┌────────────▼───────────┐
              │  game_engine.py        │ ← Owned by Zhilong (DO NOT EDIT)
              │  eval/metrics.py       │ ← Owned by Zhilong (DO NOT EDIT)
              └────────────────────────┘
```

**What GameForge generates and evaluates:**
- **God Tile configurations** — which 28 tiles exist in the pool, their stats and effects
- **Flower Card sets** — which cards are available and their balance parameters
- **Blind scaling variants** — target score curves per ante
- **Starting economy setups** — initial gold, tile material distributions

---

## HU Game Model

Understanding HU's design is essential for the agents. Key concepts:

### Tile System
- **136 tiles total**: 3 number suits (万/条/筒, values 1–9, 4 copies each) + 4 winds + 3 dragons = 34 unique types
- **Materials**: Copper/Silver/Gold/Bamboo/Ice/Glass/Glazed/Jade/Porcelain/Emerald — special properties
  - 瓷 (Porcelain): wildcard → any honor tile
  - 翡翠 (Emerald): wildcard → any number 1–9 same suit

### Hand Structure
- **14 tiles** = 4 melds (chow/pong/kong) + 1 pair
- **Win forms**: Standard (4+1), Seven Pairs (七对), Thirteen Orphans (国士无双)
- **Discard budget**: 5 discards per round; draw budget separate

### Fan Patterns (Scoring Multipliers)
| Tier | Fans | Multiplier Range |
|------|------|-----------------|
| Basic | 胡牌, 平和, 一气通贯, 三色同顺 | ×1–×2 |
| Mid | 断幺九, 混一色, 对对和, 七对, 三暗刻, 小三元, 混老头 | ×3–×8 |
| High | 清一色, 大三元, 小四喜, 四暗刻, 连七对 | ×8–×32 |
| Yakuman | 字一色, 清老头, 大四喜, 绿一色, 九莲宝灯, 国士无双 | ×20–×88 |

**Scoring Formula:**
```
finalScore = (baseScore + chipModifiers) × (fanMultiplierSum × multMultiplier + additiveMult)
baseScore  = 50 (default)
```

### Roguelike Structure
- **8 Antes**, each with 3 Blinds (Small → Big → Boss)
- **Blind targets** scale from 300 (Ante 1 Small) to 2700+ (Ante 8 Boss)
- **Between blinds**: Shop phase where player buys God Tiles and Flower Cards
- **God Tiles**: 28 tiles across 4 Bonds (Gamble/Vision/Wealth/Transform), 4 rarities (Green/Blue/Purple/Gold)
  - Bond levels unlock at 2/4/6 tiles, providing passive escalating effects
- **Flower Cards**: 32 consumables across 4 types (Plum/Bamboo/Orchid/Chrysanthemum)
  - Instant (立即生效) or On-Win (胡牌结算)

### Balance Targets
| Metric | Target Range | Notes |
|--------|-------------|-------|
| Win rate (Ante 1–2) | 65–80% | Learnable entry |
| Win rate (Ante 3–5) | 45–60% | Strategic challenge |
| Win rate (Ante 6–8) | 25–45% | Mastery required |
| Avg fan tier on win | Mid-tier by Ante 4 | Progression signal |
| God Tile purchase rate | >60% per shop | Items feel useful |
| Build archetype diversity | ≥4 viable strategies | Prevent meta lock |

---

## System Architecture

### Agent Responsibilities

#### Designer Agent
- **Role**: Proposes new content configurations using an LLM
- **Input**: Design constraints, current balance metrics, Critic feedback
- **Output**: A `ContentProposal` — a structured description of god tiles, flower cards, and scaling parameters
- **Strategy**: Chain-of-thought reasoning about game design tradeoffs; references HU fan/god tile taxonomy
- **LLM**: Any instruction-following LLM (Claude, GPT-4, Gemini); swappable

#### Simulator Agent
- **Role**: Wraps `game_engine.py` and runs N simulation episodes per proposal
- **Input**: `ContentProposal`, simulation config (N games, random seeds)
- **Output**: `SimulationReport` — raw game logs aggregated into statistics
- **Implementation**: Pure Python wrapper; no game logic lives here
- **Performance target**: 1000 games per configuration in <60 seconds

#### Balancer Agent
- **Role**: Analyzes `SimulationReport`, identifies balance problems
- **Input**: `SimulationReport` + `ContentProposal`
- **Output**: `BalanceReport` — flags OP/UP items, suggests parameter tweaks
- **Methods**: Statistical testing (z-tests for win rate deviations), item usage correlation, fan pattern frequency analysis

#### Critic Agent
- **Role**: Evaluates the meta-health of a content set — not just balance but fun
- **Input**: `ContentProposal` + `BalanceReport`
- **Output**: `CriticReport` — diversity score, fun estimate, anti-pattern flags
- **Methods**: Shannon entropy on build archetypes, homogeneity penalty if single strategy dominates

### Orchestrator
- Manages the agent pipeline: Designer → Simulator → Balancer → Critic → (loop)
- Maintains a `RunHistory` ledger for all proposals and their scores
- Implements iteration policy: accept/reject/mutate proposals
- Exposes CLI entrypoint and optionally a REST API

---

## Directory Structure

```
gameforge/
│
├── ARCHITECTURE.md          ← This document
├── README.md                ← Quick start + project overview
├── pyproject.toml           ← Python project config (uv/pip)
│
├── gameforge/               ← Main Python package
│   ├── __init__.py
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── orchestrator.py  ← Pipeline coordinator
│   │   ├── run_history.py   ← Ledger of all proposals + results
│   │   └── iteration_policy.py  ← Accept/reject/mutate logic
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py    ← Abstract base class
│   │   ├── designer.py      ← Designer Agent
│   │   ├── simulator.py     ← Simulator Agent
│   │   ├── balancer.py      ← Balancer Agent
│   │   └── critic.py        ← Critic Agent
│   │
│   ├── models/              ← Typed data models (Pydantic)
│   │   ├── __init__.py
│   │   ├── content.py       ← ContentProposal, GodTileDef, FlowerCardDef
│   │   ├── simulation.py    ← SimulationReport, GameLog, EpisodeResult
│   │   ├── balance.py       ← BalanceReport, BalanceFlag, ItemStats
│   │   └── critique.py      ← CriticReport, DiversityMetrics
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── llm_client.py    ← Abstracted LLM API (OpenAI/Anthropic/Gemini)
│   │   ├── stats.py         ← Statistical helpers (z-tests, entropy, CI)
│   │   └── serializer.py    ← JSON serialization helpers
│   │
│   └── config/
│       ├── __init__.py
│       ├── defaults.py      ← Default simulation params, LLM settings
│       └── hu_taxonomy.py   ← Fan names, god tile bonds, rarity weights
│                              (mirrors HU TypeScript data, Python side)
│
├── simulator/
│   ├── __init__.py
│   ├── game_engine.py       ← ⛔ Zhilong's (DO NOT EDIT)
│   └── engine_adapter.py    ← Thin wrapper: ContentProposal → engine calls
│
├── eval/
│   ├── __init__.py
│   ├── metrics.py           ← ⛔ Zhilong's (DO NOT EDIT)
│   └── metrics_adapter.py   ← Adapts raw logs → SimulationReport fields
│
├── runs/                    ← Runtime data (gitignored large files)
│   ├── proposals/           ← Saved ContentProposals as JSON
│   ├── reports/             ← Simulation + balance + critic reports
│   └── accepted/            ← Final accepted configurations
│
├── tests/
│   ├── test_designer.py
│   ├── test_balancer.py
│   ├── test_critic.py
│   ├── test_orchestrator.py
│   └── fixtures/            ← Sample proposals + simulation data
│
└── scripts/
    ├── run_pipeline.py      ← CLI entrypoint: run the full pipeline
    ├── inspect_run.py       ← Pretty-print a run's history
    └── export_to_hu.py      ← Convert accepted proposal → HU TypeScript data files
```

---

## Agent Interfaces

All agents implement the `BaseAgent` protocol:

```python
# gameforge/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Any

class BaseAgent(ABC):
    """All GameForge agents implement this interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable agent identifier."""
        ...

    @abstractmethod
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the agent's task.
        
        Args:
            context: Input data (typed by each agent's contract below).
        Returns:
            Output data (typed by each agent's contract below).
        Raises:
            AgentError: On unrecoverable failure.
        """
        ...
```

### Designer Agent Interface

```python
# gameforge/agents/designer.py

class DesignerInput(TypedDict):
    iteration: int                          # Current iteration number
    design_constraints: DesignConstraints   # Hard limits (see models)
    previous_results: list[IterationResult] # History of past proposals+scores
    critic_feedback: CriticReport | None    # Feedback from last Critic run

class DesignerOutput(TypedDict):
    proposal: ContentProposal    # The generated content configuration
    design_rationale: str        # LLM reasoning for this proposal
```

### Simulator Agent Interface

```python
# gameforge/agents/simulator.py

class SimulatorInput(TypedDict):
    proposal: ContentProposal    # Content to simulate
    n_games: int                 # How many games to run (default: 1000)
    seeds: list[int] | None      # Optional: fixed seeds for reproducibility
    ante_range: tuple[int, int]  # Which antes to simulate (default: 1–8)

class SimulatorOutput(TypedDict):
    report: SimulationReport     # Aggregated statistics
    raw_logs: list[GameLog]      # Per-game traces (optional, large)
```

### Balancer Agent Interface

```python
# gameforge/agents/balancer.py

class BalancerInput(TypedDict):
    proposal: ContentProposal
    report: SimulationReport

class BalancerOutput(TypedDict):
    balance_report: BalanceReport
    suggested_mutations: list[ProposalMutation]  # Concrete parameter changes
```

### Critic Agent Interface

```python
# gameforge/agents/critic.py

class CriticInput(TypedDict):
    proposal: ContentProposal
    balance_report: BalanceReport
    run_history: list[IterationResult]  # All proposals so far (for diversity)

class CriticOutput(TypedDict):
    critic_report: CriticReport
    accept: bool          # Should orchestrator accept this proposal?
    score: float          # Composite quality score [0.0, 1.0]
    feedback: str         # Natural language feedback for Designer
```

---

## Message & Data Formats

All inter-agent messages are **Pydantic models** serializable to JSON. This enables logging, replay, and easy inspection.

### ContentProposal

```python
# gameforge/models/content.py

class GodTileDef(BaseModel):
    id: str                    # e.g. "gamble_green_01"
    name: str                  # Display name
    bond: GodTileBond          # gamble | vision | wealth | transform
    rarity: GodTileRarity      # green | blue | purple | gold
    price: int                 # Gold cost in shop
    effect_type: str           # Enum: "chips_add", "mult_add", "mult_multiply",
                               #       "gold_add", "probability", "transform"
    effect_value: float        # Numeric effect magnitude
    effect_condition: str | None  # e.g. "has_dragon", "fan:清一色"

class FlowerCardDef(BaseModel):
    id: str
    card_type: FlowerCardType  # plum | bamboo | orchid | chrysanthemum
    trigger: Literal["instant", "on_win"]
    name: str
    cost: int
    effect_type: str
    effect_value: float | None

class BlindScaling(BaseModel):
    """Target score = base + (ante - 1) * step"""
    small_base: int = 300
    small_step: int = 150
    big_base: int = 450
    big_step: int = 225
    boss_base: int = 600
    boss_step: int = 300

class ContentProposal(BaseModel):
    proposal_id: str               # UUID
    iteration: int
    created_at: datetime
    god_tiles: list[GodTileDef]    # Must have exactly 7 per bond × 4 bonds = 28
    flower_cards: list[FlowerCardDef]  # 8 per type × 4 types = 32
    blind_scaling: BlindScaling
    starting_gold: int = 4
    design_rationale: str          # LLM's explanation
```

### SimulationReport

```python
# gameforge/models/simulation.py

class EpisodeResult(BaseModel):
    seed: int
    ante_reached: int              # How far the player got (1–8)
    final_ante_cleared: bool
    rounds_played: int
    fans_used: dict[str, int]      # Fan name → frequency across all rounds
    god_tiles_purchased: list[str] # God tile IDs bought during run
    flower_cards_used: list[str]
    build_archetype: str           # Inferred: "triplets" | "flush" | "honors" | "mixed" | etc.
    per_blind_scores: list[float]  # Score achieved per blind attempt

class SimulationReport(BaseModel):
    proposal_id: str
    n_games: int
    ante_range: tuple[int, int]
    
    # Primary metrics
    win_rate_by_ante: dict[int, float]    # ante → fraction of runs that cleared
    avg_rounds_per_run: float
    
    # Fan pattern statistics
    fan_frequency: dict[str, float]       # fan_name → fraction of wins containing it
    avg_fan_multiplier_on_win: float
    
    # God Tile & economy
    god_tile_purchase_rate: dict[str, float]  # tile_id → purchase rate
    avg_gold_per_ante: dict[int, float]
    
    # Derived by metrics.py (Zhilong's)
    win_rate_distribution: list[float]    # Per-game win/loss sequence
    build_archetype_counts: dict[str, int]
    
    episodes: list[EpisodeResult]         # Full per-game records
```

### BalanceReport

```python
# gameforge/models/balance.py

class BalanceSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class BalanceFlag(BaseModel):
    severity: BalanceSeverity
    item_type: Literal["god_tile", "flower_card", "blind", "global"]
    item_id: str | None
    metric: str            # e.g. "win_rate_ante_1", "purchase_rate"
    observed: float
    expected_range: tuple[float, float]
    description: str

class ProposalMutation(BaseModel):
    """A concrete suggested parameter change."""
    item_id: str
    field: str             # e.g. "effect_value", "price"
    current_value: float
    suggested_value: float
    reason: str

class BalanceReport(BaseModel):
    proposal_id: str
    overall_health: float          # [0, 1] — 1 = perfectly balanced
    flags: list[BalanceFlag]
    op_items: list[str]            # God tile IDs flagged as overpowered
    up_items: list[str]            # God tile IDs flagged as underpowered
    suggested_mutations: list[ProposalMutation]
```

### CriticReport

```python
# gameforge/models/critique.py

class DiversityMetrics(BaseModel):
    shannon_entropy: float         # Build archetype diversity [0, log(N)]
    dominant_archetype: str | None # Most common build (if >40% → warning)
    dominant_archetype_rate: float
    unique_builds_seen: int        # Of N games, how many distinct archetypes

class CriticReport(BaseModel):
    proposal_id: str
    diversity: DiversityMetrics
    
    fun_score: float               # [0, 1] — estimated enjoyment proxy
    novelty_score: float           # [0, 1] — how different from prior proposals
    anti_patterns: list[str]       # e.g. "meta_lock", "snowball_dominance"
    
    composite_score: float         # Weighted final quality score
    accept: bool
    feedback_for_designer: str     # Natural language critique
```

---

## Agent Interaction Protocol

### Orchestrator Flow

```
for iteration in 1..MAX_ITERATIONS:
    
    1. Designer.run({
           iteration,
           design_constraints,
           previous_results,
           critic_feedback  ← from last iteration's Critic output
       })
       → ContentProposal
    
    2. Simulator.run({
           proposal,
           n_games = 1000,
           seeds = [0..999],
           ante_range = (1, 8)
       })
       → SimulationReport
    
    3. Balancer.run({
           proposal,
           report = SimulationReport
       })
       → BalanceReport
    
    4. Critic.run({
           proposal,
           balance_report,
           run_history
       })
       → CriticReport
    
    5. if CriticReport.accept and BalanceReport.overall_health > 0.75:
           SAVE proposal to runs/accepted/
           NOTIFY Zhilong
           BREAK
       else:
           APPEND to run_history
           CONTINUE with next iteration
```

### Iteration Policy

```python
# gameforge/orchestrator/iteration_policy.py

class IterationPolicy:
    """Decide what to do after each Critic report."""
    
    def decide(self, history: list[IterationResult]) -> IterationDecision:
        """
        Returns one of:
          ACCEPT     — quality threshold met, stop
          MUTATE     — apply Balancer's suggested mutations, re-simulate
          REDESIGN   — reset and ask Designer for a fresh proposal
          FAIL       — too many iterations, surface to Zhilong
        """
```

**Default policy parameters:**
- `MAX_ITERATIONS = 20`
- `ACCEPT_THRESHOLD = composite_score >= 0.75`
- `MUTATE_THRESHOLD = composite_score >= 0.50` (try fixing before redesigning)
- After 3 consecutive MUTATE cycles → force REDESIGN

---

## Tool Inventory

| Tool | Used By | Purpose |
|------|---------|---------|
| LLM API (Claude/GPT/Gemini) | Designer, Critic | Content generation, feedback synthesis |
| `game_engine.py` | Simulator (via adapter) | Simulating mahjong game runs |
| `eval/metrics.py` | Simulator (via adapter) | Computing win rates, diversity scores |
| Pydantic | All agents | Schema validation, serialization |
| `scipy.stats` | Balancer | Z-tests for win rate deviation from target |
| `numpy` | Balancer, Critic | Statistical computations |
| `scipy.stats.entropy` | Critic | Shannon entropy for build diversity |
| JSON file I/O | Orchestrator | Persisting proposals and reports in `runs/` |
| `pytest` | Tests | Unit + integration testing |
| `uv` | Dev | Python package management |

### LLM Client Abstraction

```python
# gameforge/tools/llm_client.py

class LLMClient(Protocol):
    def complete(self, prompt: str, system: str = "") -> str: ...

class AnthropicClient:
    """Uses claude-3-5-sonnet (default) or configurable."""

class OpenAIClient:
    """Uses gpt-4o (default) or configurable."""

class GeminiClient:
    """Uses gemini-2.0-flash or configurable."""
```

The Designer and Critic accept any `LLMClient` — swap models freely.

---

## Evaluation Metrics

These metrics are computed from `SimulationReport` (feeding from Zhilong's `metrics.py`):

### 1. Win Rate Distribution
**Definition:** For each Ante level, the fraction of game runs where the player cleared all 3 blinds in that Ante.

**Target range:** 45%–55% overall (with natural progression: easier early antes, harder late antes).

**Balance flags:**
- Win rate > 70% at any Ante → content too easy (OP items)
- Win rate < 20% at Ante 1 → too hard for new players (UP content or scaling too steep)

### 2. Build Archetype Diversity (Shannon Entropy)
**Definition:** Shannon entropy H of the build archetype distribution across N simulated games.
```
H = -Σ p(archetype_i) × log(p(archetype_i))
```
**Archetypes:** triplets, chow-based, flush (half/full), honors, seven-pairs, mixed

**Target:** H ≥ 1.5 (out of theoretical max ~1.79 for 6 equal archetypes). Below 1.0 → meta lock warning.

### 3. Average Game Rounds
**Definition:** Mean number of blind attempts across all game runs.

**Target:** 15–25 rounds per full run (roughly Antes 1–5 average completion). A run too short suggests snowball; too long suggests stall.

### 4. God Tile Purchase Rate
**Definition:** Per god tile, fraction of games where it was purchased when offered.

**Target:** 40%–80%. Below 20% → tile feels weak/overpriced. Above 90% → dominates shop decisions.

### 5. Fan Pattern Frequency
**Definition:** Per fan pattern, fraction of winning hands containing it.

**Target:** No single fan should appear in >60% of wins (except 胡牌 which is universal). Mid/high-tier fans should be viable (>10% each in late antes).

---

## Boundaries

> **Files owned by Zhilong — GameForge reads but never writes these:**

| File | Why Off-Limits |
|------|----------------|
| `simulator/game_engine.py` | Core mahjong rule engine; correctness is paramount |
| `eval/metrics.py` | Win rate + diversity scoring logic; authoritative source |

GameForge interacts with these exclusively through adapter layers (`engine_adapter.py`, `metrics_adapter.py`) that translate GameForge types to/from whatever interfaces Zhilong defines.

**Contract assumption:** `game_engine.py` will expose a callable that accepts a `ContentProposal`-compatible dict and returns per-game results. The exact interface will be finalized when Zhilong implements it.

---

## Open Questions for Review

These are design decisions that need Zhilong's input before implementation:

1. **`game_engine.py` interface** — What's the expected input/output signature? Does it accept a config dict, or will there be a class-based API?

2. **"Deck content" scope** — Should GameForge propose mutations to existing HU content (e.g., tweak existing god tile values), or always propose fully synthetic new content sets? The architecture supports both, but the Designer's LLM prompt strategy differs significantly.

3. **Simulation speed** — Is 1000 games per proposal feasible in <60s on your machine? If not, should we use parallel processes (multiprocessing) or reduce to 500 games?

4. **Archetype inference** — How should the Simulator classify a run's "build archetype" (triplets/flush/etc.)? Should this come from `game_engine.py`, or should GameForge infer it from `fans_used` frequencies?

5. **LLM budget** — The Designer calls an LLM every iteration. With up to 20 iterations per pipeline run, costs add up. Preferred model + budget ceiling?

6. **Export format** — `scripts/export_to_hu.py` converts accepted proposals back into HU TypeScript files (`godTiles.ts`, `flowerCards.ts`). Should this be auto-applied or require manual approval?

7. **Acceptance criteria** — Is `composite_score >= 0.75` the right threshold? Should Zhilong always be notified for human approval before a proposal is marked "accepted"?

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-03-08 | HU Dev Agent | Initial architecture draft (Phase 1) |

---

*Pending Zhilong's review and approval before Phase 2 (implementation) begins.*
