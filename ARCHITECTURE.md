# GameForge — AI Game Development Studio

**Status:** Phase 1 Architecture Design (Pending Review)
**Last Updated:** 2026-03-10
**Author:** Friday + Zhilong

---

## What Is GameForge?

GameForge is a multi-agent framework that turns a game design document into a playable, deployed game — end to end. No human coding required (but human review at every milestone).

```
Human writes game_design.md
         ↓
    ┌─────────┐
    │ Producer │ → execution_plan.json (human reviews & approves)
    └─────────┘
         ↓
    ┌──────────────────────────────┐
    │  Round 1: Core Engine        │ ← Design → Implement → Playtest → Fix loop
    │  Round 2: Game Systems       │
    │  Round 3: Adapter (if needed)│
    │  Round 4: Content & Balance  │
    │  Round 5: Polish & Deploy    │
    └──────────────────────────────┘
         ↓
    Playable game
```

---

## Three Layers

### Layer 1: Producer
Reads the game design, generates a detailed execution plan. Does not write code.

### Layer 2: Dev Loop
Three agents cycle on each task: Designer → Implementer → Playtester. Loops until exit criteria met.

### Layer 3: Game Adapter (optional)
Headless interface to the game engine for high-volume automated playtesting (1000+ simulations). Only built when the game has numerical balance needs.

---

## Layer 1: Producer Agent

### Input
A `game_design.md` written by the human. Contains:
- Game genre and concept
- Core mechanics
- Target platform
- Art style / tech preferences
- Known constraints

### Output
An `execution_plan.json` — the complete blueprint for building the game.

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

  "adapter_needed": true,
  "adapter_reason": "Game has numerical balance (god tiles, flower cards, difficulty scaling) requiring statistical playtesting",

  "rounds": [
    {
      "id": 1,
      "name": "Core Mahjong Engine",
      "goal": "Player can complete one hand of mahjong with correct fan scoring",
      "playtest_mode": "ui",
      "tasks": [
        {
          "id": "1.1",
          "name": "Tile system and hand representation",
          "agent": "implementer",
          "model": "claude-opus-4-6",
          "system_context": "Implement a mahjong tile system: 136 tiles (3 number suits × 9 values × 4 copies + 4 winds × 4 + 3 dragons × 4). Support hand operations: draw, discard, chow, pong, kong. Use TypeScript with strict types.",
          "files_to_create": ["src/engine/tiles.ts", "src/engine/hand.ts"],
          "acceptance": "Unit tests pass for all tile operations",
          "depends_on": []
        },
        {
          "id": "1.2",
          "name": "Win detection and fan scoring",
          "agent": "implementer",
          "model": "claude-opus-4-6",
          "system_context": "Implement mahjong win detection (standard 4+1, seven pairs, thirteen orphans) and fan pattern scoring. Reference fan table: 胡牌 ×1, 平和 ×1, 清一色 ×8, 国士无双 ×88, etc.",
          "files_to_create": ["src/engine/win-detector.ts", "src/engine/fan-scorer.ts"],
          "acceptance": "All 34 fan patterns correctly identified and scored against test cases",
          "depends_on": ["1.1"]
        },
        {
          "id": "1.3",
          "name": "Basic game UI — table, hand, discard",
          "agent": "implementer",
          "model": "claude-opus-4-6",
          "system_context": "Build a Phaser 3 scene showing: player's 14-tile hand, discard pile, draw button, tile selection for discard. Dark theme. Mobile-first layout (portrait).",
          "files_to_create": ["src/scenes/GameScene.ts", "src/ui/TileSprite.ts"],
          "acceptance": "Player can see hand, tap to select, discard, draw, and win a hand visually",
          "depends_on": ["1.2"]
        }
      ],
      "exit_criteria": "Human plays one complete hand in browser. Fan score displays correctly. No crashes.",
      "human_review": true
    },

    {
      "id": 2,
      "name": "Roguelike Loop",
      "goal": "Player can progress through Ante 1–8 with shop phases between blinds",
      "playtest_mode": "ui",
      "tasks": [
        {
          "id": "2.1",
          "name": "Ante/Blind progression system",
          "agent": "implementer",
          "model": "claude-opus-4-6",
          "system_context": "Implement 8 Antes, each with 3 Blinds (Small/Big/Boss). Target scores scale per ante. Player must reach target score in one hand to clear a blind. Track gold earned per clear.",
          "files_to_create": ["src/engine/progression.ts"],
          "acceptance": "Game progresses through all 8 antes with correct target scaling",
          "depends_on": []
        },
        {
          "id": "2.2",
          "name": "Shop system",
          "agent": "implementer",
          "model": "claude-opus-4-6",
          "system_context": "Between blinds, show a shop offering god tiles and flower cards for purchase with gold. Implement inventory, purchase, and equip logic.",
          "files_to_create": ["src/engine/shop.ts", "src/scenes/ShopScene.ts"],
          "acceptance": "Player can buy items, gold deducted, items appear in inventory",
          "depends_on": ["2.1"]
        },
        {
          "id": "2.3",
          "name": "God tile effects",
          "agent": "designer",
          "model": "claude-opus-4-6",
          "system_context": "Design 28 god tiles (4 bonds × 7 tiles). Each has: name, bond, rarity, price, effect_type, effect_value, trigger_condition. Bonds: Gamble (high risk/reward), Vision (information advantage), Wealth (economy), Transform (tile manipulation). Output as structured JSON.",
          "output_format": "json",
          "acceptance": "28 tiles with no duplicate effects, reasonable value ranges, all 4 bonds feel distinct",
          "depends_on": []
        },
        {
          "id": "2.4",
          "name": "Implement god tile effects",
          "agent": "implementer",
          "model": "claude-opus-4-6",
          "system_context": "Implement the god tile effect system. Each tile hooks into scoring, draw, discard, or shop events. Load tile definitions from JSON. Support bond-level bonuses at 2/4/6 tiles.",
          "files_to_create": ["src/engine/god-tiles.ts", "src/data/god-tiles.json"],
          "acceptance": "All 28 tile effects trigger correctly during gameplay",
          "depends_on": ["2.2", "2.3"]
        }
      ],
      "exit_criteria": "Human plays Ante 1 through Ante 3, buys god tiles, uses flower cards. Feels like a roguelike.",
      "human_review": true
    },

    {
      "id": 3,
      "name": "Game Adapter",
      "goal": "Headless game engine for automated batch simulation",
      "playtest_mode": "none",
      "condition": "adapter_needed == true",
      "tasks": [
        {
          "id": "3.1",
          "name": "Headless engine wrapper",
          "agent": "implementer",
          "model": "claude-opus-4-6",
          "system_context": "Create a headless wrapper around the game engine that can run a full Ante 1–8 game without any UI. Accept a content config (god tiles, flower cards, scaling) as JSON input. Output per-game results as JSON.",
          "files_to_create": ["src/adapter/headless-engine.ts", "src/adapter/types.ts"],
          "acceptance": "Can run 100 games via CLI in under 30 seconds",
          "depends_on": []
        },
        {
          "id": "3.2",
          "name": "AI player strategies",
          "agent": "implementer",
          "model": "claude-opus-4-6",
          "system_context": "Implement greedy AI player strategies: discard selection (minimize shanten), shop buying (cost-efficiency), flower card usage (use when beneficial). Support multiple strategy profiles: aggressive, conservative, balanced, random.",
          "files_to_create": ["src/adapter/ai-player.ts", "src/adapter/strategies.ts"],
          "acceptance": "AI can complete full runs. Different strategies produce measurably different outcomes.",
          "depends_on": ["3.1"]
        },
        {
          "id": "3.3",
          "name": "Batch simulator and statistics",
          "agent": "implementer",
          "model": "claude-opus-4-6",
          "system_context": "Run N games with M strategies, aggregate results: win rate by ante, god tile purchase rates, fan pattern frequency, build archetype distribution, Shannon entropy of strategies.",
          "files_to_create": ["src/adapter/batch-sim.ts", "src/adapter/stats.ts"],
          "acceptance": "1000-game batch produces valid statistical report matching expected format",
          "depends_on": ["3.2"]
        }
      ],
      "exit_criteria": "Batch simulation of 1000 games completes in <60s with valid statistics output.",
      "human_review": true
    },

    {
      "id": 4,
      "name": "Content & Balance",
      "goal": "All content balanced: 4+ viable strategies, win rates within target ranges",
      "playtest_mode": "adapter",
      "tasks": [
        {
          "id": "4.1",
          "name": "Balance analysis and iteration",
          "agent": "designer",
          "model": "claude-opus-4-6",
          "system_context": "Analyze batch simulation results. Identify overpowered/underpowered god tiles (purchase rate >90% or <20%), unviable strategies (archetype <5% representation), and difficulty spikes (win rate drops >30% between consecutive antes). Propose parameter adjustments.",
          "acceptance": "Win rate by ante within targets: Ante 1-2 (65-80%), Ante 3-5 (45-60%), Ante 6-8 (25-45%). Shannon entropy of build archetypes >= 1.5. No single god tile with >90% purchase rate.",
          "depends_on": []
        },
        {
          "id": "4.2",
          "name": "Exploit detection",
          "agent": "playtester",
          "model": "claude-opus-4-6",
          "system_context": "You are a game tester trying to break the game. Look at god tile combinations that produce degenerate strategies: infinite loops, guaranteed wins, zero-risk infinite gold. Report any combo that trivializes the game.",
          "acceptance": "No known exploits remain. All flagged combos reviewed and fixed.",
          "depends_on": ["4.1"]
        }
      ],
      "exit_criteria": "3 consecutive batch runs meet all balance targets. No known exploits.",
      "human_review": true
    },

    {
      "id": 5,
      "name": "Polish & Deploy",
      "goal": "Production-ready game deployed to target platform",
      "playtest_mode": "ui",
      "tasks": [
        {
          "id": "5.1",
          "name": "Visual polish",
          "agent": "implementer",
          "model": "claude-opus-4-6",
          "system_context": "Add animations (tile draw, discard, win celebration), sound effects, screen transitions. Follow the existing dark theme. Mobile-first.",
          "acceptance": "Game feels responsive and polished. No visual glitches on mobile.",
          "depends_on": []
        },
        {
          "id": "5.2",
          "name": "Platform deployment",
          "agent": "implementer",
          "model": "claude-opus-4-6",
          "system_context": "Package as YouTube Playable: single HTML5 bundle, <5MB, touch controls, 9:16 portrait. Set up build pipeline.",
          "acceptance": "Game loads and plays correctly as YouTube Playable.",
          "depends_on": ["5.1"]
        }
      ],
      "exit_criteria": "Game deployed and playable on target platform. Human does final playthrough.",
      "human_review": true
    }
  ]
}
```

### Producer Responsibilities

1. **Read** `game_design.md`
2. **Analyze** scope — what systems are needed, what's the tech stack
3. **Decide** `adapter_needed` — does this game need statistical balancing?
4. **Decompose** into rounds with clear goals and dependencies
5. **Generate** per-task agent assignments with:
   - Which agent (designer / implementer / playtester)
   - Recommended model
   - System context (what the agent needs to know)
   - Acceptance criteria
   - File dependencies
6. **Output** `execution_plan.json`
7. **Wait** for human review and approval before execution begins

### Human Review Points

Every round ends with `"human_review": true`. The human:
- Plays the game (for UI playtest rounds)
- Reviews the execution plan before each round starts
- Can modify tasks, reorder, add/remove
- Approves to proceed or sends back for replanning

**GameForge never auto-proceeds past a round without human approval.**

---

## Layer 2: Dev Loop

Each task within a round runs through a three-agent loop:

```
┌──────────┐     ┌─────────────┐     ┌────────────┐
│ Designer │────→│ Implementer │────→│ Playtester  │
│          │     │             │     │             │
│ "What"   │     │ "Build it"  │     │ "Test it"   │
└──────────┘     └─────────────┘     └────────────┘
      ↑                ↑                    │
      │                │                    │
      │                └── 🐛 Bug ──────────┤
      │                                     │
      └──── 😴 Boring / 📊 Imbalanced ─────┘
```

### Agent Roles

#### Designer Agent
- **Job**: Define what to build — game mechanics, content specs, UI layouts
- **Input**: Task description from execution plan + feedback from Playtester
- **Output**: Structured design document (JSON, markdown, or spec)
- **When active**: New feature design, redesign after "boring" or "too hard" feedback
- **Not involved in**: Bug fixes (those go straight to Implementer)

#### Implementer Agent
- **Job**: Write code that realizes the design
- **Input**: Design spec + codebase context + bug reports
- **Output**: Working code (committed to repo)
- **Model**: Coding-optimized (Claude Opus, Codex)
- **When active**: Initial implementation + bug fix cycles

#### Playtester Agent
- **Job**: Play the game (via UI or adapter) and report findings
- **Input**: Running game instance or simulation results
- **Output**: Structured feedback report

Playtester feedback is categorized and routed:

| Feedback Type | Routed To | Example |
|---|---|---|
| 🐛 **Bug** | → Implementer | "Score shows NaN after winning with seven pairs" |
| 😴 **Boring** | → Designer | "Every game I just buy the cheapest god tiles and win" |
| 📊 **Too Hard** | → Designer | "Can't clear Ante 3 no matter what strategy I use" |
| 📊 **Too Easy** | → Designer | "Beat Ante 8 on first try without any god tiles" |
| ✅ **Pass** | → Next task | "Plays as expected, no issues found" |

### Playtest Modes

| Mode | How It Works | Speed | Best For |
|---|---|---|---|
| **UI** | Agent controls the game through browser (click, observe) | Slow (minutes/game) | UX bugs, visual issues, feel |
| **Adapter** | Agent calls headless engine, runs 1000+ games | Fast (seconds/batch) | Balance, statistics, exploits |

Early rounds use UI mode. Balance rounds use Adapter mode.

### Loop Termination

A task's loop ends when:
- Playtester reports ✅ **Pass** (meets acceptance criteria)
- **Max iterations reached** (default: 5 design cycles, 10 bug fix cycles) → escalate to human
- **Human override** — human can force-accept or force-redesign at any point

---

## Layer 3: Game Adapter (Optional)

The adapter is a **headless interface** to the game engine, enabling high-volume automated playtesting without rendering UI.

### When Is It Needed?

| Game Type | Adapter Needed? | Why |
|---|---|---|
| Roguelike with items/stats | ✅ Yes | Need to balance hundreds of items across thousands of runs |
| Card game with deck building | ✅ Yes | Need to test deck balance statistically |
| Narrative adventure | ❌ No | Balance isn't numerical; UI playtesting is sufficient |
| Puzzle game | ⚠️ Maybe | If difficulty curves need tuning |

The Producer sets `adapter_needed` based on the game design. If true, a dedicated Adapter Round is scheduled.

### Adapter Interface

```typescript
interface GameAdapter {
  // Core
  gameName: string;
  
  // Content definition
  contentSchema(): JSONSchema;           // What content looks like
  designConstraints(): Constraints;       // Hard limits for Designer
  balanceTargets(): BalanceTargets;        // What "balanced" means
  gameTaxonomy(): string;                 // Natural language game concepts for LLM

  // Simulation
  simulate(config: ContentConfig, options: SimOptions): SimulationReport;
  
  // Strategy classification
  classifyBuild(episode: EpisodeResult): string;
  
  // Export
  export(config: ContentConfig, outputDir: string): string[];
}
```

### Adapter Components

1. **Headless Engine** — runs the game logic without any UI
2. **AI Player Strategies** — algorithmic players (greedy, aggressive, conservative) that make decisions deterministically
3. **Batch Simulator** — runs N games × M strategies, aggregates statistics
4. **Statistics Module** — win rates, entropy, usage rates, exploit detection

The AI players are **not LLMs** — they're simple algorithmic strategies (e.g., "discard the tile furthest from winning"). They need to be consistent, not smart. The goal is measuring **relative differences between content configurations**, not optimal play.

---

## Execution Flow

```
1. Human writes game_design.md
2. Producer reads it → generates execution_plan.json
3. Human reviews plan → approves / edits
4. For each round:
   a. Show round summary to human
   b. For each task in round:
      - Assign to agent (designer / implementer / playtester)
      - Run dev loop until acceptance criteria met or max iterations
      - Commit code after each implementation cycle
   c. Round complete → human playtests → approves to proceed
5. Game deployed
```

### Example: HU Development Timeline

```
Round 1: Core Engine (Week 1)
  1.1 Tile system          → Implementer builds, Playtester verifies unit tests
  1.2 Win detection + fans → Implementer builds, Playtester runs test cases
  1.3 Basic UI             → Implementer builds, Playtester plays via browser
  → Human plays one hand ✅

Round 2: Roguelike Loop (Week 2)
  2.1 Ante/Blind system    → Implementer builds
  2.2 Shop system          → Implementer builds
  2.3 God tile design      → Designer creates 28 tiles as JSON
  2.4 God tile effects     → Implementer codes effects
  → Human plays Ante 1-3 ✅

Round 3: Adapter (Week 3, first half)
  3.1 Headless wrapper     → Implementer builds
  3.2 AI strategies        → Implementer builds 4 strategy profiles
  3.3 Batch simulator      → Implementer builds
  → 1000-game batch completes in <60s ✅

Round 4: Balance (Week 3, second half)
  4.1 Balance iteration    → Designer analyzes stats, tweaks values
  4.2 Exploit detection    → Playtester tries to break the game
  → 3 clean batch runs ✅

Round 5: Polish & Deploy (Week 4)
  5.1 Animations + sound   → Implementer adds polish
  5.2 YouTube Playable     → Implementer packages and deploys
  → Live on YouTube Playables ✅
```

---

## Design Principles

1. **Human-in-the-loop**: GameForge never auto-proceeds past a milestone. Every round requires human approval.

2. **Feedback drives routing**: Playtester categorizes issues (bug → Implementer, design problem → Designer). The loop self-organizes.

3. **Adapter is earned, not assumed**: Not every game needs statistical balancing. The Producer decides, and the adapter is built as an explicit round.

4. **Execution plan is the contract**: Everything is specified upfront — agents, models, context, criteria. No ambiguity during execution.

5. **Game-agnostic framework**: The three layers (Producer, Dev Loop, Adapter) work for any game genre. Only the adapter internals are game-specific.

---

## Open Questions

1. **Playtester vision**: For UI playtest mode, how does the agent observe the game? Screenshot analysis? DOM inspection? Game state API?

2. **Implementer context window**: Large codebases may exceed context limits. Should each task get a fresh agent with only relevant files, or maintain a persistent session?

3. **Designer-Implementer handoff**: Should the Designer output be a strict JSON schema (Implementer follows exactly) or a natural language spec (Implementer has creative freedom)?

4. **Cross-round state**: When Round 4 balance tweaks affect Round 2 code, how do we handle regressions? Run Round 2 exit criteria as a regression test?

5. **Parallel tasks**: Within a round, independent tasks (e.g., 2.1 and 2.3) could run in parallel. Should the Producer mark parallelizable tasks?

6. **Cost control**: With multiple agents running loops, LLM costs can escalate. Should the execution plan include per-task token budgets?

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-03-08 | HU Dev Agent | Initial draft (HU-specific pipeline) |
| 2026-03-10 | Friday | Refactored to game-agnostic framework with GameAdapter |
| 2026-03-10 | Friday + Zhilong | Complete redesign: Producer → Dev Loop → Adapter architecture |
