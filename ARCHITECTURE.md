# GameForge — AI Game Development Studio

**Status:** Phase 1 Architecture Design (Pending Review)
**Last Updated:** 2026-03-10
**Author:** Friday + Zhilong

---

## What Is GameForge?

GameForge turns a game design document into a playable, deployed game using three AI agents in a continuous loop. A human reviews at milestones but never micromanages the process.

```
Human writes game_design.md
         ↓
    ┌─────────┐
    │ Producer │ → execution_plan.json (milestones + agent configs)
    └─────────┘
         ↓
    ┌────────────┐
    │ Translator │ → runnable multi-agent code (AutoGen / CrewAI / LangGraph / OpenClaw)
    └────────────┘
         ↓
    ┌─────────────────────────────────────────┐
    │                                         │
    │   Designer ⇄ Implementer ⇄ Playtester  │
    │              continuous loop             │
    │                                         │
    │   ── Milestone 1 ── human review ✅ ──  │
    │   ── Milestone 2 ── human review ✅ ──  │
    │   ── Milestone 3 ── human review ✅ ──  │
    │   ── Milestone 4 ── done 🎉            │
    │                                         │
    └─────────────────────────────────────────┘
         ↓
    Playable game
```

---

## Core Idea

The entire development process is **one continuous loop** of three agents:

```
┌──────────┐     ┌─────────────┐     ┌────────────┐
│ Designer │────→│ Implementer │────→│ Playtester  │
│          │     │             │     │             │
│ "What to │     │ "Build it"  │     │ "Test it"   │
│  build"  │     │             │     │             │
└──────────┘     └─────────────┘     └────────────┘
      ↑                ↑                    │
      │                │                    │
      │                └── 🐛 Bug ──────────┤
      │                                     │
      └──── 😴 Boring / 📊 Imbalanced ─────┘
```

The loop runs continuously. Agents decide among themselves what to work on next. The only interruptions are **milestones** — checkpoints where the system pauses for human review.

**This is not a pipeline.** Agents communicate freely:
- Playtester finds a bug → tells Implementer directly
- Playtester says "boring" → tells Designer to rethink
- Implementer has a question about spec → asks Designer
- Designer wants to validate an idea quickly → asks Implementer for a prototype

---

## Four Layers

### Layer 1: Producer
Reads `game_design.md`, generates `execution_plan.json` with milestones and agent configurations. Does not prescribe tasks — agents self-organize toward each milestone.

### Layer 2: Translator
Converts the execution plan into runnable multi-agent code for a specific framework. Pluggable — swap runtimes without changing the plan.

### Layer 3: Dev Loop
The three agents (Designer, Implementer, Playtester) run in a continuous cycle, self-organizing their work toward each milestone.

### Layer 4: Game Adapter (optional)
Headless interface to the game engine for high-volume automated playtesting. Built by the agents themselves when needed, not pre-defined.

---

## Layer 1: Producer Agent

### Input
A `game_design.md` written by the human.

### Output
An `execution_plan.json`:

```json
{
  "game": {
    "name": "HU",
    "genre": "Roguelike Mahjong Deck-Builder",
    "platform": "Web (YouTube Playables)",
    "stack": {
      "engine": "Phaser 3",
      "language": "TypeScript",
      "build": "Vite"
    }
  },

  "agents": {
    "designer": {
      "model": "claude-opus-4-6",
      "system_context": "You are a game designer for a roguelike mahjong deck-builder called HU. You design game mechanics, content (god tiles, flower cards), difficulty curves, and UI layouts. You output structured specs (JSON or markdown). When the Playtester reports something is boring or imbalanced, you propose design changes. You do not write code.",
      "tools": ["file_read", "file_write"]
    },
    "implementer": {
      "model": "claude-opus-4-6",
      "system_context": "You are a game developer building HU, a roguelike mahjong deck-builder using Phaser 3 + TypeScript + Vite. You implement features from Designer specs and fix bugs from Playtester reports. You commit code to git after each change. You follow existing code patterns and maintain type safety.",
      "tools": ["file_read", "file_write", "git_commit", "terminal"]
    },
    "playtester": {
      "model": "claude-opus-4-6",
      "system_context": "You are a game tester for HU, a roguelike mahjong deck-builder. You play the game and report findings. Categorize each finding as: BUG (send to Implementer), BORING/TOO_HARD/TOO_EASY (send to Designer), or PASS (milestone criteria met). When an adapter is available, you can also run batch simulations for statistical analysis.",
      "tools": ["browser_control", "batch_simulate"],
      "playtest_modes": {
        "ui": "Control game through browser — observe visuals, interactions, feel",
        "adapter": "Run headless simulations — statistical balance analysis (available after agents build it)"
      }
    }
  },

  "milestones": [
    {
      "id": 1,
      "name": "Playable Hand",
      "goal": "Player can complete one full hand of mahjong with correct fan scoring displayed",
      "exit_criteria": [
        "All 3 win forms work (standard, seven pairs, thirteen orphans)",
        "Fan scoring matches expected values for 10 test hands",
        "UI shows hand, discard area, score breakdown",
        "No crashes during a full hand"
      ],
      "human_review": true
    },
    {
      "id": 2,
      "name": "Roguelike Loop",
      "goal": "Player can progress through Ante 1–8 with shop phases, god tiles, and flower cards",
      "exit_criteria": [
        "8 Antes × 3 Blinds with correct target scaling",
        "Shop appears between blinds with purchasable items",
        "God tile effects trigger correctly during gameplay",
        "Flower cards can be used and consumed",
        "Player can reach Ante 8 (not necessarily win)"
      ],
      "human_review": true
    },
    {
      "id": 3,
      "name": "Content Balance",
      "goal": "All content balanced with diverse viable strategies",
      "adapter_hint": "Statistical playtesting recommended — agents should build a headless adapter if not already done",
      "exit_criteria": [
        "Win rate by ante within targets: Ante 1-2 (65-80%), Ante 3-5 (45-60%), Ante 6-8 (25-45%)",
        "Build archetype Shannon entropy >= 1.5 (4+ viable strategies)",
        "No god tile with >90% purchase rate (OP) or <20% (UP)",
        "No known exploits or degenerate combos",
        "3 consecutive batch runs (1000 games each) meet all targets"
      ],
      "human_review": true
    },
    {
      "id": 4,
      "name": "Ship It",
      "goal": "Production-ready game deployed to target platform",
      "exit_criteria": [
        "Animations, sound effects, transitions polished",
        "Mobile-friendly (touch controls, portrait 9:16)",
        "Bundle <5MB for YouTube Playables",
        "Final human playthrough with no issues"
      ],
      "human_review": true
    }
  ]
}
```

### What the Producer Does NOT Do

- ❌ Define specific tasks or work items
- ❌ Assign tasks to specific agents
- ❌ Prescribe implementation order
- ❌ Decide how agents communicate

The Producer defines **where to go** (milestones). The agents decide **how to get there**.

---

## Layer 2: Translator

Converts `execution_plan.json` into runnable multi-agent code for a specific framework.

### Why a Separate Layer?

The execution plan is **framework-agnostic** — it describes milestones and agent configs, not orchestration mechanics. Different teams use different frameworks. The Translator adapts the plan to your runtime.

```
execution_plan.json
        │
   ┌────┴────┐
   │Translator│
   └────┬────┘
        │
   ┌────┴──────────────────────────────┐
   │  AutoGen  │ CrewAI │ LangGraph │ OpenClaw │
   └───────────────────────────────────┘
```

### Translator Interface

```python
class Translator(ABC):
    @abstractmethod
    def translate(self, plan: ExecutionPlan) -> ProjectFiles:
        """
        Input:  execution_plan.json
        Output: Runnable source files for the target framework.
        """
        ...
```

### AutoGen Translator (Reference Implementation)

Generates:
- **Agent definitions** with system prompts from `agents.*. system_context`
- **GroupChat** with free-form communication (agents talk to each other, not routed by a pipeline)
- **Milestone checker** — after each Playtester turn, evaluate exit criteria; if all met, pause for human
- **Tool bindings** — file I/O, git, browser control, terminal
- **Human gate** — blocks between milestones until human approves

### Supported Translators

| Translator | Runtime | Communication Model |
|---|---|---|
| `AutoGenTranslator` | Microsoft AutoGen | GroupChat — agents speak freely |
| `CrewAITranslator` | CrewAI | Crew with delegation enabled |
| `LangGraphTranslator` | LangChain/LangGraph | State graph with dynamic routing |
| `OpenClawTranslator` | OpenClaw | `sessions_spawn` + `sessions_send` |

---

## Layer 3: Dev Loop

### The Three Agents

#### Designer
- **Job**: Define what to build — mechanics, content, UI specs
- **Communicates with**: Implementer (hands off specs), Playtester (receives design feedback)
- **Does not**: Write code

#### Implementer
- **Job**: Write code, fix bugs, commit to git
- **Communicates with**: Designer (asks for clarification), Playtester (receives bug reports)
- **Does not**: Decide what to build (follows Designer's specs)

#### Playtester
- **Job**: Play the game and report findings
- **Communicates with**: Implementer (bug reports), Designer (design feedback)
- **Does not**: Write code or design features

### Feedback Routing

Playtester categorizes every finding. Routing is automatic:

| Finding | Category | Sent To | Example |
|---|---|---|---|
| Something broken | 🐛 **BUG** | Implementer | "Score shows NaN after seven pairs win" |
| Not fun | 😴 **BORING** | Designer | "Same strategy wins every time" |
| Too hard | 📊 **TOO_HARD** | Designer | "Can't clear Ante 3 regardless of strategy" |
| Too easy | 📊 **TOO_EASY** | Designer | "Beat Ante 8 on first try without items" |
| All good | ✅ **PASS** | Milestone check | "Meets all exit criteria" |

### Free-Form Communication

Unlike a rigid pipeline, agents can talk to each other at any time:

```
Designer: "Here's the spec for the shop system: [JSON spec]"
Implementer: "Should the shop refresh between blinds or only between antes?"
Designer: "Between blinds. Updated spec: [JSON]"
Implementer: "Done. Shop implemented, committed."
Playtester: "Shop works but I can buy infinite items — gold goes negative."
Implementer: "Fixed. Added gold check before purchase."
Playtester: "Works now. But the shop only shows 3 items, feels empty."
Designer: "Good point. Increase to 5 items, add reroll button for 1 gold."
Implementer: "Done."
Playtester: "PASS ✅"
```

### Playtest Modes

| Mode | How | Speed | When |
|---|---|---|---|
| **UI** | Agent controls game through browser | Minutes/game | Early milestones — catching bugs, UX issues |
| **Adapter** | Headless engine, 1000+ batch simulations | Seconds/batch | Balance milestone — statistical analysis |

The adapter is **not pre-built** — when the agents reach the balance milestone and realize they need batch testing, they build the adapter themselves as part of the loop. The `adapter_hint` in the milestone tells them this is expected.

### Loop Termination

The loop for a milestone ends when:
- Playtester reports ✅ **PASS** on all exit criteria
- **Max iterations reached** (configurable, default: 50 agent turns per milestone) → escalate to human
- **Human override** — human can force-proceed or force-redo at any review point

---

## Layer 4: Game Adapter (Optional)

A headless interface to the game engine for batch simulation. **Built by the agents, not pre-defined.**

### When Is It Needed?

The Producer sets `adapter_hint` on milestones that likely need statistical playtesting. The agents decide when and how to build it.

| Game Type | Adapter Likely? | Why |
|---|---|---|
| Roguelike with items | ✅ Yes | Balance hundreds of items across thousands of runs |
| Card game | ✅ Yes | Deck balance requires statistical testing |
| Narrative game | ❌ No | No numerical balance needed |
| Puzzle game | ⚠️ Maybe | Difficulty curve tuning |

### What the Agents Build

When they need an adapter, the Implementer creates:

1. **Headless Engine** — game logic without UI, accepts content config as JSON
2. **AI Player Strategies** — algorithmic players (greedy, aggressive, conservative)
3. **Batch Runner** — runs N games × M strategies, outputs statistics
4. **Stats Module** — win rates, Shannon entropy, usage rates, exploit detection

The AI players are **not LLMs** — they're deterministic algorithms (minimize shanten, maximize cost-efficiency). Consistent, fast, cheap. The goal is measuring **relative differences between configurations**, not optimal play.

### Adapter Interface

```typescript
interface GameAdapter {
  gameName: string;
  contentSchema(): JSONSchema;
  designConstraints(): Constraints;
  balanceTargets(): BalanceTargets;
  gameTaxonomy(): string;
  simulate(config: ContentConfig, options: SimOptions): SimulationReport;
  classifyBuild(episode: EpisodeResult): string;
  export(config: ContentConfig, outputDir: string): string[];
}
```

---

## Design Principles

1. **One continuous loop**: No artificial rounds or task assignments. Three agents cycle freely toward milestones.

2. **Milestones, not tasks**: Producer defines where to go (exit criteria), not how to get there. Agents self-organize.

3. **Human-in-the-loop at milestones**: GameForge pauses at every milestone for human review. Never auto-proceeds.

4. **Feedback drives routing**: Playtester categorizes issues → automatically routed to the right agent. The loop self-organizes.

5. **Adapter is emergent**: Not pre-built. When agents need batch testing, they build it themselves. The milestone hints at this but doesn't mandate it.

6. **Runtime-agnostic**: The execution plan is framework-independent. Swap AutoGen for CrewAI by changing the Translator — everything else stays the same.

7. **Execution plan is the contract**: Agent configs, milestones, and exit criteria are all specified upfront. No ambiguity during execution.

---

## Example: Building HU

```
Human: "Here's game_design.md for HU, a roguelike mahjong deck-builder"

Producer → execution_plan.json:
  - 4 milestones: Playable Hand → Roguelike Loop → Content Balance → Ship It
  - 3 agent configs with system contexts
  - adapter_hint on Milestone 3

Translator (AutoGen) → generates runnable GroupChat code

=== Milestone 1: Playable Hand ===

Designer: "Let me define the tile system and fan scoring rules..."
  → outputs tile_spec.json, fan_table.json
Implementer: reads specs, builds tiles.ts, win-detector.ts, fan-scorer.ts, GameScene.ts
Playtester: plays in browser
  → "BUG: 国士无双 not detected when I have all terminals + honors"
Implementer: fixes win detector
Playtester: plays again
  → "PASS ✅ All 3 win forms work, scoring correct"

→ Human review: plays a hand, looks good ✅ proceed

=== Milestone 2: Roguelike Loop ===

Designer: "Here's the ante/blind system, shop, 28 god tiles, 32 flower cards..."
Implementer: builds progression, shop, god tile effects
Playtester: plays Ante 1-3
  → "BUG: gold doesn't reset between runs"
Implementer: fixes
Playtester: plays again
  → "BORING: I just buy the cheapest god tiles and win easily"
Designer: rethinks pricing, adds bond synergy requirements
Implementer: implements changes
Playtester: plays again
  → "PASS ✅ Feels like a roguelike now"

→ Human review: plays through Ante 5, good progression ✅ proceed

=== Milestone 3: Content Balance ===

Designer: "We need statistical data. Let's build a headless adapter."
Implementer: builds headless-engine.ts, ai-player.ts, batch-sim.ts
Playtester: runs 1000 games
  → "TOO_EASY: Ante 1-4 win rate >85%. Gamble bond dominates (70% of builds)"
Designer: nerfs gamble bond, buffs vision/transform
Implementer: updates values
Playtester: runs 1000 games again
  → "Better. But 翡翠 tile + 赌博第3张 = infinite gold exploit"
Implementer: adds gold cap per turn
Playtester: runs 1000 games
  → "PASS ✅ All targets met, entropy 1.6, no exploits"

→ Human review: checks stats, runs a few games manually ✅ proceed

=== Milestone 4: Ship It ===

Designer: "Add win animations, tile flip effects, shop transition"
Implementer: adds polish, packages for YouTube Playables
Playtester: final playthrough on mobile
  → "BUG: touch target too small on god tiles in shop"
Implementer: increases hit area
Playtester: "PASS ✅"

→ Human review: final playthrough ✅ deploy 🎉
```

---

## Open Questions

1. **Agent memory**: As the codebase grows, how do agents maintain context? Persistent sessions? RAG over the repo? Summarized state passed each turn?

2. **Playtester vision**: For UI playtest mode, how does the agent observe the game? Screenshot + vision model? DOM inspection? Game state API exposed to browser console?

3. **Conflict resolution**: What if Designer and Playtester disagree? ("This is intentionally hard" vs "This is unfairly hard") Who wins? Escalate to human?

4. **Parallel work**: Can Designer spec the next feature while Implementer is still coding the current one? Or strictly sequential turns?

5. **Cost control**: With free-form agent communication, token usage is unpredictable. Should there be per-milestone budgets?

6. **Regression testing**: When changes for Milestone 3 break Milestone 1 functionality, how is this detected? Automated test suite built incrementally?

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-03-08 | HU Dev Agent | Initial draft (HU-specific pipeline) |
| 2026-03-10 | Friday | Refactored to game-agnostic framework with GameAdapter |
| 2026-03-10 | Friday + Zhilong | Redesigned: Producer → Translator → continuous Dev Loop with milestones |
