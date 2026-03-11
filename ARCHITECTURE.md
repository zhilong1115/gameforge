# GameForge — Multi-Agent Game Content Generation Framework

**Status:** Phase 1 Architecture Design (Pending Review)
**Last Updated:** 2026-03-10
**Author:** Friday

---

## Table of Contents

1. [Overview](#overview)
2. [Design Philosophy](#design-philosophy)
3. [System Architecture](#system-architecture)
4. [Game Adapter Interface](#game-adapter-interface)
5. [Agent Interfaces](#agent-interfaces)
6. [Message & Data Formats](#message--data-formats)
7. [Agent Interaction Protocol](#agent-interaction-protocol)
8. [Evaluation Framework](#evaluation-framework)
9. [Directory Structure](#directory-structure)
10. [Tool Inventory](#tool-inventory)
11. [Example: HU Adapter](#example-hu-adapter)
12. [Open Questions for Review](#open-questions-for-review)

---

## Overview

**GameForge** is a game-agnostic multi-agent framework for automated content generation, simulation-driven testing, and balance optimization. Four specialized AI agents form an iterative pipeline:

1. **Designer** — proposes new content configurations using LLM reasoning
2. **Simulator** — stress-tests proposals by running thousands of game episodes
3. **Balancer** — statistically analyzes simulation results to detect balance issues
4. **Critic** — evaluates meta-health (diversity, fun, novelty) and decides accept/reject

The framework is **game-agnostic**: it defines abstract interfaces for game rules, content schemas, and evaluation metrics. Concrete games plug in via a `GameAdapter` — a thin layer that translates game-specific concepts into GameForge's universal protocol.

```
┌──────────────────────────────────────────────────────────────┐
│                    GameForge Framework                        │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Designer │→ │Simulator │→ │ Balancer │→ │  Critic  │    │
│  │ (LLM)    │  │(Engine)  │  │(Stats)   │  │(Quality) │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│       ↑                                         │            │
│       └─────────── feedback loop ───────────────┘            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              GameAdapter (Abstract)                     │  │
│  │  - content_schema()    - simulate()                    │  │
│  │  - design_constraints() - classify_build()             │  │
│  │  - balance_targets()   - export()                      │  │
│  └────────────────────────────────────────────────────────┘  │
│       ▲            ▲            ▲            ▲               │
│  ┌────┴───┐  ┌────┴───┐  ┌────┴───┐  ┌────┴───┐           │
│  │  HU    │  │  RPG   │  │  CCG   │  │ Puzzle │           │
│  │Adapter │  │Adapter │  │Adapter │  │Adapter │           │
│  └────────┘  └────────┘  └────────┘  └────────┘           │
└──────────────────────────────────────────────────────────────┘
```

**Key differentiator:** Most game balancing tools are hard-coded for one game. GameForge separates the _what_ (game-specific content) from the _how_ (multi-agent generation and evaluation pipeline), making it reusable across genres.

---

## Design Philosophy

### 1. Game-Agnostic Core
The framework knows nothing about specific games. It operates on abstract concepts:
- **Content** — a structured proposal (schema defined by the adapter)
- **Episodes** — simulated game runs producing measurable outcomes
- **Metrics** — numeric signals (win rate, diversity, economy health)
- **Feedback** — natural language critique driving the next iteration

### 2. Clean Agent Boundaries
Each agent has a typed input/output contract. Agents communicate only through the Orchestrator via structured messages (Pydantic models serializable to JSON). No shared mutable state — enables independent testing, swapping, and parallelization.

### 3. LLM as Reasoning Engine, Not Magic
The Designer and Critic use LLMs for _reasoning about design tradeoffs_, not for generating arbitrary code. The LLM proposes structured content (validated by schema), and the Simulator + Balancer verify it empirically. This grounds LLM creativity in measurable outcomes.

### 4. Iteration Over Perfection
The pipeline is explicitly iterative. A proposal is rarely accepted on the first try — the Critic's feedback steers the Designer toward better designs over multiple rounds. This mirrors how human game designers iterate.

---

## System Architecture

### Agent Responsibilities

#### Designer Agent
- **Role**: Proposes new content configurations using LLM chain-of-thought reasoning
- **Input**: Design constraints, balance targets, iteration history, Critic feedback
- **Output**: A `ContentProposal` — structured content matching the game's schema
- **Strategy**: References game taxonomy, previous failures, and Critic suggestions to generate increasingly better proposals
- **LLM**: Any instruction-following model (Claude, GPT-4, Gemini); swappable via `LLMClient`

#### Simulator Agent
- **Role**: Runs N game episodes per proposal using the game engine
- **Input**: `ContentProposal` + simulation config (N episodes, seeds, difficulty range)
- **Output**: `SimulationReport` — aggregated statistics from all episodes
- **Implementation**: Delegates to `GameAdapter.simulate()`; no game logic lives in the agent

#### Balancer Agent
- **Role**: Statistical analysis of simulation results against balance targets
- **Input**: `SimulationReport` + `ContentProposal` + `BalanceTargets`
- **Output**: `BalanceReport` — flags problems (OP/UP items, pacing issues), suggests parameter mutations
- **Methods**: Z-tests for metric deviations, correlation analysis, distribution tests

#### Critic Agent
- **Role**: Evaluates meta-health — not just balance, but diversity, fun, and novelty
- **Input**: `ContentProposal` + `BalanceReport` + run history
- **Output**: `CriticReport` — composite quality score, accept/reject decision, natural language feedback
- **Methods**: Shannon entropy for strategy diversity, novelty scoring against prior proposals, anti-pattern detection

### Orchestrator
- Manages the pipeline loop: Designer → Simulator → Balancer → Critic → (iterate)
- Maintains `RunHistory` ledger across iterations
- Implements `IterationPolicy`: accept / mutate / redesign / fail
- Exposes CLI entrypoint and optional REST API

---

## Game Adapter Interface

The `GameAdapter` is the **only thing you implement** to plug a new game into GameForge.

```python
# gameforge/adapters/base.py

from abc import ABC, abstractmethod
from typing import Any

class GameAdapter(ABC):
    """
    Abstract interface between GameForge and a specific game.
    Implement this to plug any game into the framework.
    """

    @property
    @abstractmethod
    def game_name(self) -> str:
        """Human-readable game name."""
        ...

    @abstractmethod
    def content_schema(self) -> dict:
        """
        Returns a JSON Schema describing valid ContentProposal structure
        for this game. Used by Designer for structured output and validation.
        """
        ...

    @abstractmethod
    def design_constraints(self) -> DesignConstraints:
        """
        Returns hard constraints the Designer must respect.
        E.g., exactly 28 items, cost range [1, 10], etc.
        """
        ...

    @abstractmethod
    def balance_targets(self) -> BalanceTargets:
        """
        Returns target metric ranges for the Balancer.
        E.g., win_rate per difficulty level, item usage rates, etc.
        """
        ...

    @abstractmethod
    def game_taxonomy(self) -> str:
        """
        Returns a natural language description of game concepts,
        terminology, and design space. Fed to Designer LLM as context.
        """
        ...

    @abstractmethod
    def simulate(
        self,
        proposal: dict,
        n_episodes: int,
        seeds: list[int] | None = None,
        difficulty_range: tuple[int, int] = (1, 8),
    ) -> SimulationReport:
        """
        Run n_episodes of the game with the given content proposal.
        Returns aggregated statistics.
        """
        ...

    @abstractmethod
    def classify_build(self, episode: EpisodeResult) -> str:
        """
        Classify a single game episode into a strategy archetype.
        E.g., "aggressive", "control", "combo", etc.
        """
        ...

    @abstractmethod
    def export(self, proposal: dict, output_dir: str) -> list[str]:
        """
        Convert an accepted proposal into game-native format files.
        Returns list of generated file paths.
        """
        ...
```

### What the Adapter Provides

| Method | Purpose | Example (roguelike) | Example (CCG) |
|--------|---------|---------------------|---------------|
| `content_schema()` | What content looks like | Item defs + scaling curves | Card defs + deck rules |
| `design_constraints()` | Hard limits | "Exactly 28 items, 4 categories" | "60-card pool, 5 rarities" |
| `balance_targets()` | What "balanced" means | Win rate 45-55% per level | Deck win rate 48-52% |
| `game_taxonomy()` | LLM context | Item types, scoring rules | Keywords, mana curve |
| `simulate()` | Run the game engine | 1000 roguelike runs | 1000 bot-vs-bot matches |
| `classify_build()` | Strategy labeling | "flush build", "combo build" | "aggro", "control", "midrange" |
| `export()` | Output to game files | TypeScript data files | JSON card definitions |

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
            context: Input data (typed per agent contract).
        Returns:
            Output data (typed per agent contract).
        Raises:
            AgentError: On unrecoverable failure.
        """
        ...
```

### Designer Agent Contract

```python
class DesignerInput(TypedDict):
    iteration: int
    content_schema: dict              # From GameAdapter
    design_constraints: DesignConstraints
    balance_targets: BalanceTargets
    game_taxonomy: str                # Natural language game context
    previous_results: list[IterationResult]
    critic_feedback: CriticReport | None

class DesignerOutput(TypedDict):
    proposal: dict                    # Validated against content_schema
    design_rationale: str             # LLM reasoning
```

### Simulator Agent Contract

```python
class SimulatorInput(TypedDict):
    proposal: dict
    n_episodes: int                   # Default: 1000
    seeds: list[int] | None
    difficulty_range: tuple[int, int]

class SimulatorOutput(TypedDict):
    report: SimulationReport
```

### Balancer Agent Contract

```python
class BalancerInput(TypedDict):
    proposal: dict
    report: SimulationReport
    balance_targets: BalanceTargets

class BalancerOutput(TypedDict):
    balance_report: BalanceReport
    suggested_mutations: list[ProposalMutation]
```

### Critic Agent Contract

```python
class CriticInput(TypedDict):
    proposal: dict
    balance_report: BalanceReport
    run_history: list[IterationResult]

class CriticOutput(TypedDict):
    critic_report: CriticReport
    accept: bool
    score: float                      # Composite quality [0.0, 1.0]
    feedback: str                     # Natural language for Designer
```

---

## Message & Data Formats

All inter-agent messages are **Pydantic models** serializable to JSON.

### Core Models (Game-Agnostic)

```python
# gameforge/models/core.py

class SimulationReport(BaseModel):
    """Aggregated results from N game episodes."""
    proposal_id: str
    n_episodes: int
    difficulty_range: tuple[int, int]
    
    # Primary metrics (game-agnostic)
    win_rate_by_difficulty: dict[int, float]
    avg_episode_length: float
    
    # Strategy diversity
    build_archetype_counts: dict[str, int]
    
    # Item/content usage rates
    content_usage_rates: dict[str, float]   # content_id → usage fraction
    
    # Per-episode records
    episodes: list[EpisodeResult]
    
    # Extensible: adapters can add game-specific metrics
    extra_metrics: dict[str, Any] = {}

class EpisodeResult(BaseModel):
    """Single game episode outcome."""
    seed: int
    difficulty_reached: int
    completed: bool
    rounds_played: int
    content_used: list[str]           # IDs of content items used
    build_archetype: str
    scores: list[float]               # Per-round/level scores
    extra: dict[str, Any] = {}        # Game-specific data

class BalanceTargets(BaseModel):
    """What 'balanced' means for this game."""
    win_rate_targets: dict[int, tuple[float, float]]  # difficulty → (min, max)
    content_usage_range: tuple[float, float]           # (min, max) per item
    min_strategy_diversity: float                       # Min Shannon entropy
    extra_targets: dict[str, Any] = {}

class DesignConstraints(BaseModel):
    """Hard limits on content proposals."""
    content_counts: dict[str, int]    # category → exact count required
    value_ranges: dict[str, tuple[float, float]]  # field → (min, max)
    extra_constraints: dict[str, Any] = {}
```

### Balance & Critique Models

```python
# gameforge/models/balance.py

class BalanceSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class BalanceFlag(BaseModel):
    severity: BalanceSeverity
    content_type: str              # e.g., "item", "scaling", "global"
    content_id: str | None
    metric: str
    observed: float
    expected_range: tuple[float, float]
    description: str

class ProposalMutation(BaseModel):
    """A concrete suggested parameter change."""
    content_id: str
    field: str
    current_value: float
    suggested_value: float
    reason: str

class BalanceReport(BaseModel):
    proposal_id: str
    overall_health: float          # [0, 1]
    flags: list[BalanceFlag]
    op_items: list[str]
    up_items: list[str]
    suggested_mutations: list[ProposalMutation]

# gameforge/models/critique.py

class DiversityMetrics(BaseModel):
    shannon_entropy: float
    dominant_archetype: str | None
    dominant_archetype_rate: float
    unique_builds_seen: int

class CriticReport(BaseModel):
    proposal_id: str
    diversity: DiversityMetrics
    fun_score: float               # [0, 1]
    novelty_score: float           # [0, 1]
    anti_patterns: list[str]
    composite_score: float
    accept: bool
    feedback_for_designer: str
```

---

## Agent Interaction Protocol

### Orchestrator Flow

```
adapter = load_adapter(game_name)  # e.g., HUAdapter, RPGAdapter

for iteration in 1..MAX_ITERATIONS:
    
    1. Designer.run({
           iteration,
           content_schema   = adapter.content_schema(),
           design_constraints = adapter.design_constraints(),
           balance_targets  = adapter.balance_targets(),
           game_taxonomy    = adapter.game_taxonomy(),
           previous_results,
           critic_feedback
       })
       → ContentProposal
    
    2. Simulator.run({
           proposal,
           n_episodes = 1000,
           # delegates to adapter.simulate()
       })
       → SimulationReport
    
    3. Balancer.run({
           proposal,
           report,
           balance_targets = adapter.balance_targets()
       })
       → BalanceReport
    
    4. Critic.run({
           proposal,
           balance_report,
           run_history
       })
       → CriticReport
    
    5. IterationPolicy.decide(history) →
           ACCEPT   → save to runs/accepted/, notify, break
           MUTATE   → apply mutations, re-simulate
           REDESIGN → fresh Designer proposal
           FAIL     → surface to human after MAX_ITERATIONS
```

### Iteration Policy

```python
class IterationPolicy:
    MAX_ITERATIONS = 20
    ACCEPT_THRESHOLD = 0.75        # composite_score
    MUTATE_THRESHOLD = 0.50
    MAX_CONSECUTIVE_MUTATES = 3    # Force redesign after 3 failed mutations
    
    def decide(self, history: list[IterationResult]) -> IterationDecision:
        """ACCEPT | MUTATE | REDESIGN | FAIL"""
```

---

## Evaluation Framework

These metrics are computed from `SimulationReport` and are **game-agnostic**:

### 1. Win Rate Distribution
Per difficulty level, the fraction of episodes completed. Compared against `BalanceTargets.win_rate_targets`.

### 2. Strategy Diversity (Shannon Entropy)
```
H = -Σ p(archetype_i) × log(p(archetype_i))
```
Higher entropy = more diverse viable strategies. Target: `BalanceTargets.min_strategy_diversity`.

### 3. Content Usage Rates
Per content item, fraction of episodes where it was used/purchased. Flags items that are always picked (OP) or never picked (UP).

### 4. Episode Length Distribution
Mean and variance of rounds per episode. Too short = snowball; too long = stall.

### 5. Composite Score
Weighted combination of balance health, diversity, and novelty:
```python
composite = (
    w_balance * balance_report.overall_health +
    w_diversity * normalize(diversity.shannon_entropy) +
    w_novelty * novelty_score
)
```
Weights are configurable per game via the adapter.

---

## Directory Structure

```
gameforge/
│
├── ARCHITECTURE.md          ← This document
├── README.md
├── pyproject.toml
│
├── gameforge/               ← Framework package
│   ├── __init__.py
│   │
│   ├── orchestrator/
│   │   ├── orchestrator.py        ← Pipeline coordinator
│   │   ├── run_history.py         ← Iteration ledger
│   │   └── iteration_policy.py    ← Accept/reject/mutate logic
│   │
│   ├── agents/
│   │   ├── base_agent.py          ← Abstract base class
│   │   ├── designer.py            ← Designer Agent
│   │   ├── simulator.py           ← Simulator Agent
│   │   ├── balancer.py            ← Balancer Agent
│   │   └── critic.py              ← Critic Agent
│   │
│   ├── adapters/
│   │   ├── base.py                ← GameAdapter abstract interface
│   │   └── registry.py            ← Adapter discovery + loading
│   │
│   ├── models/
│   │   ├── core.py                ← ContentProposal, SimulationReport, EpisodeResult
│   │   ├── balance.py             ← BalanceReport, BalanceFlag, ProposalMutation
│   │   ├── critique.py            ← CriticReport, DiversityMetrics
│   │   └── targets.py             ← BalanceTargets, DesignConstraints
│   │
│   ├── tools/
│   │   ├── llm_client.py          ← Abstracted LLM API
│   │   ├── stats.py               ← Statistical helpers
│   │   └── serializer.py          ← JSON helpers
│   │
│   └── config/
│       └── defaults.py            ← Default pipeline params
│
├── adapters/                ← Game-specific adapters (separate from core)
│   └── hu/
│       ├── __init__.py
│       ├── adapter.py             ← HUAdapter(GameAdapter)
│       ├── taxonomy.py            ← HU game concepts for LLM context
│       ├── schema.py              ← HU content JSON schema
│       ├── engine_bridge.py       ← Wraps HU's game_engine.py
│       └── exporter.py            ← Converts proposals → HU TypeScript files
│
├── runs/                    ← Runtime data (gitignored)
│   ├── proposals/
│   ├── reports/
│   └── accepted/
│
├── tests/
│   ├── test_designer.py
│   ├── test_balancer.py
│   ├── test_critic.py
│   ├── test_orchestrator.py
│   └── fixtures/
│
└── scripts/
    ├── run_pipeline.py            ← CLI: gameforge run --game hu
    └── inspect_run.py             ← Pretty-print run history
```

---

## Tool Inventory

| Tool | Used By | Purpose |
|------|---------|---------|
| LLM API (Claude/GPT/Gemini) | Designer, Critic | Content generation, feedback synthesis |
| Game Engine (via adapter) | Simulator | Running game episodes |
| Pydantic | All agents | Schema validation, serialization |
| `scipy.stats` | Balancer | Z-tests, distribution analysis |
| `numpy` | Balancer, Critic | Statistical computations |
| `scipy.stats.entropy` | Critic | Shannon entropy for diversity |
| JSON file I/O | Orchestrator | Persisting proposals and reports |
| `pytest` | Tests | Unit + integration testing |
| `uv` | Dev | Python package management |

### LLM Client Abstraction

```python
class LLMClient(Protocol):
    def complete(self, prompt: str, system: str = "") -> str: ...

# Swappable implementations:
# AnthropicClient, OpenAIClient, GeminiClient
```

---

## Example: HU Adapter

To demonstrate how a game plugs into GameForge, here's a sketch of the HU adapter (roguelike mahjong deck-builder):

```python
# adapters/hu/adapter.py

class HUAdapter(GameAdapter):
    game_name = "HU"
    
    def content_schema(self) -> dict:
        """28 God Tiles (4 bonds × 7) + 32 Flower Cards (4 types × 8) + scaling."""
        return HU_CONTENT_SCHEMA
    
    def design_constraints(self) -> DesignConstraints:
        return DesignConstraints(
            content_counts={"god_tiles": 28, "flower_cards": 32},
            value_ranges={"price": (1, 10), "effect_value": (0.1, 50.0)},
        )
    
    def balance_targets(self) -> BalanceTargets:
        return BalanceTargets(
            win_rate_targets={
                1: (0.65, 0.80),  # Ante 1: learnable
                4: (0.45, 0.60),  # Mid-game: strategic
                8: (0.25, 0.45),  # Endgame: mastery
            },
            content_usage_range=(0.20, 0.90),
            min_strategy_diversity=1.5,
        )
    
    def simulate(self, proposal, n_episodes, seeds, difficulty_range):
        """Wraps Zhilong's game_engine.py via engine_bridge."""
        return self.engine_bridge.run(proposal, n_episodes, seeds)
    
    def classify_build(self, episode) -> str:
        """Infer archetype from fan pattern frequencies."""
        # "flush", "triplets", "honors", "seven_pairs", "mixed"
        ...
    
    def export(self, proposal, output_dir) -> list[str]:
        """Generate godTiles.ts and flowerCards.ts for HU project."""
        ...
```

Other potential adapters:
- **CCG Adapter** — card game balancing (deck win rates, mana curves)
- **RPG Adapter** — skill tree / item balancing (DPS distribution, build diversity)
- **Puzzle Adapter** — level difficulty curves (solve rates, hint usage)

---

## Open Questions for Review

1. **Adapter granularity** — Should `simulate()` be a single method, or split into `setup_episode()` + `run_episode()` + `collect_results()` for finer control?

2. **Content schema validation** — Should the framework validate proposals against `content_schema()` before passing to Simulator, or trust the Designer to produce valid output?

3. **Parallel simulation** — Should the Simulator support multiprocessing by default? This is adapter-dependent (some engines aren't thread-safe).

4. **LLM budget policy** — The Designer calls an LLM every iteration (up to 20). Should we enforce a per-run token budget, or let the adapter configure this?

5. **Human-in-the-loop** — Should accepted proposals always require human approval, or can the pipeline auto-accept above a threshold?

6. **Adapter discovery** — Plugin-based (entry points) or simple registry dict? For now, a registry is simpler.

7. **Metric extensibility** — The `extra_metrics` / `extra` fields allow adapters to pass game-specific data. Is this sufficient, or should there be a formal extension mechanism?

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-03-08 | HU Dev Agent | Initial draft (HU-specific) |
| 2026-03-10 | Friday | Refactored to game-agnostic framework with GameAdapter interface |
