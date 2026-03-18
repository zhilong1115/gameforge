# GameForge — AI Game Development Studio

**Status:** Phase 2 Architecture (Approved)
**Last Updated:** 2026-03-17
**Author:** Zhilong + Friday

---

## What Is GameForge?

GameForge takes a Game Design Document (GDD) and builds a playable game using multi-agent AI. Human reviews at milestone checkpoints but doesn't micromanage the process.

**Input:** GDD (human-written)
**Output:** Playable game with balanced mechanics

---

## Architecture Overview

Two frameworks working together:
- **LangGraph** — deterministic orchestration between milestones
- **AutoGen** — free-form multi-agent discussion within milestones

```
Input: game_design.md (GDD)
         ↓
┌─────────────────────────────────────────────┐
│              LangGraph (Orchestrator)         │
│                                               │
│  ┌──────────┐                                │
│  │ Producer  │ → Parse GDD → Split Milestones │
│  └────┬─────┘                                │
│       ↓                                       │
│  ┌──────────────────────────────────┐        │
│  │      Milestone Loop              │        │
│  │                                  │        │
│  │  ┌─────────────────────────┐    │        │
│  │  │   AutoGen GroupChat     │    │        │
│  │  │                         │    │        │
│  │  │  Designer ↔ Critic      │    │        │
│  │  │  (discuss design)       │    │        │
│  │  │       ↓                 │    │        │
│  │  │  Coder (generate code)  │    │        │
│  │  │       ↓                 │    │        │
│  │  │  Critic (review code)   │    │        │
│  │  └────────┬────────────────┘    │        │
│  │           ↓                      │        │
│  │  ┌─────────────────┐           │        │
│  │  │   Playtester    │           │        │
│  │  │ (run game_engine│           │        │
│  │  │  simulate games)│           │        │
│  │  └────────┬────────┘           │        │
│  │           ↓                      │        │
│  │  ┌─────────────────────────┐    │        │
│  │  │   AutoGen GroupChat     │    │        │
│  │  │  Balancer + Critic      │    │        │
│  │  │  (analyze + adjust)     │    │        │
│  │  └────────┬────────────────┘    │        │
│  │           ↓                      │        │
│  │     Playtest Pass? ──No──→ Loop │        │
│  │           │                      │        │
│  │          Yes                     │        │
│  └───────────┼──────────────────────┘        │
│              ↓                                │
│  ┌──────────────────────┐                    │
│  │  🧑 Human Checkpoint  │                    │
│  │  Review & Approve     │                    │
│  │  ✅ → Next Milestone  │                    │
│  │  🔄 → Adjust & Retry  │                    │
│  │  ❌ → Modify GDD      │                    │
│  └──────────┬───────────┘                    │
│             ↓                                 │
│       Next Milestone...                       │
└─────────────────────────────────────────────┘
         ↓
    Output: Playable Game 🎮
```

---

## Framework Responsibilities

### LangGraph (Project Manager)
- Parse GDD into ordered Milestones
- Manage global state (code files, test results, design decisions)
- Enforce milestone dependencies (1.3 needs 1.1 + 1.2)
- Human-in-the-loop checkpoints (`interrupt_before`)
- Decide: continue, retry, or escalate to human
- Checkpoint/resume support (can pause and continue later)

### AutoGen (Team Meetings)
- Multi-agent free-form discussion within each task
- Designer proposes → Critic challenges → iterate until consensus
- Coder generates → Critic reviews → iterate until approved
- Balancer analyzes data → suggests changes → Critic validates
- Natural conversation, not rigid tool calls

---

## Agents

| Agent | Role | Framework |
|-------|------|-----------|
| **Producer** | Reads GDD, creates milestone plan, manages dependencies | LangGraph node |
| **Designer** | Proposes game mechanics, data structures, rules | AutoGen participant |
| **Critic** | Reviews all proposals, challenges assumptions, ensures quality | AutoGen participant |
| **Coder** | Generates game code from design specs | AutoGen participant + tool calls |
| **Playtester** | Runs game_engine simulations, collects statistics | Algorithmic (not LLM) |
| **Balancer** | Analyzes playtest data, proposes numerical adjustments | AutoGen participant |

---

## Milestone Example (HU - Mahjong Roguelike)

```
GDD: HU - Roguelike Mahjong Deck-builder

Milestone 1: Core Mahjong Round
├─ Task 1.1: Tile data structures (136 tiles, suits, honors)
├─ Task 1.2: Draw/discard logic
├─ Task 1.3: Win detection (胡牌判定)
└─ Playtest: Can complete a basic round ✅
    → 🧑 Human Review

Milestone 2: Deck-building Mechanics
├─ Task 2.1: Flower tile system (passive effects)
├─ Task 2.2: Chi/Pon/Kan → flower tile selection (2/3/5 choose 1)
├─ Task 2.3: Kan multiplier ×3
└─ Playtest: Flower tiles affect game balance ✅
    → 🧑 Human Review

Milestone 3: Roguelike Layer
├─ Task 3.1: Multi-round structure
├─ Task 3.2: Shop / upgrade system
├─ Task 3.3: God tiles + synergies (gambling/insight/fortune/transform)
└─ Playtest: Multi-game loop is engaging ✅
    → 🧑 Human Review

Milestone 4: Balance & Polish
├─ Task 4.1: Numerical tuning (1000-game simulation)
├─ Task 4.2: AI opponent difficulty curve
└─ Playtest: Win rate 45-55%, no dominant strategy ✅
    → 🧑 Human Review → Ship! 🚀
```

---

## Task Execution Flow (within a Milestone)

```python
# Each task follows this cycle:

1. Producer assigns task from milestone plan
2. AutoGen GroupChat: Designer + Critic
   - Designer proposes implementation
   - Critic asks questions, finds gaps
   - Iterate 2-5 rounds until consensus
   - Output: design_spec.json

3. AutoGen GroupChat: Coder + Critic
   - Coder generates code based on design_spec
   - Critic reviews code quality, correctness
   - Iterate until code passes review
   - Output: source files written to disk

4. Playtester (algorithmic, no LLM)
   - Run game_engine with new code
   - Simulate N games
   - Collect stats: win rate, avg score, etc.
   - Output: playtest_results.json

5. AutoGen GroupChat: Balancer + Critic
   - Balancer analyzes playtest_results
   - If balanced → task complete ✅
   - If not → propose adjustments → back to step 2
```

---

## Simulator (Playtester) Design

The Playtester is **algorithmic, not LLM-based**:
- Uses greedy/heuristic strategy functions (not GPT calls per hand)
- Runs 100-1000 simulated games quickly
- Collects statistics: win rates, score distributions, strategy dominance
- Reports data back to LangGraph state for Balancer to analyze

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | LangGraph (Python) |
| Agent Chat | AutoGen (Python) |
| LLM | Claude/GPT-4 for agents (API) |
| Game Engine | Python (game_engine.py) |
| Code Generation | LLM + file I/O tools |
| State | LangGraph checkpointing |
| Human Review | LangGraph interrupt_before |

---

## Project Structure

```
gameforge/
├── ARCHITECTURE.md          # This file
├── producer/
│   ├── producer.py          # GDD parser → milestone plan
│   └── planner.py           # Task dependency graph
├── agents/
│   ├── designer.py          # AutoGen Designer agent
│   ├── critic.py            # AutoGen Critic agent
│   ├── coder.py             # AutoGen Coder agent
│   └── balancer.py          # AutoGen Balancer agent
├── orchestrator/
│   ├── graph.py             # LangGraph workflow definition
│   └── state.py             # Global state schema
├── simulator/
│   ├── game_engine.py       # Core game logic (mahjong)
│   ├── strategies.py        # AI player strategies (greedy)
│   └── runner.py            # Run N simulations
├── translator/
│   └── autogen_translator.py # Translate execution plan → AutoGen config
├── eval/
│   ├── metrics.py           # Balance metrics
│   └── report.py            # Generate playtest reports
└── games/
    └── hu/
        └── game_design.md   # HU's GDD
```

---

## Key Design Decisions

1. **GDD is human input** — GameForge doesn't generate game concepts
2. **LangGraph for flow, AutoGen for discussion** — best of both frameworks
3. **Human-in-the-loop at milestones** — not fully autonomous, practical engineering
4. **Playtester is algorithmic** — greedy strategies, not LLM per hand (too slow/expensive)
5. **Milestone-based iteration** — build incrementally, each milestone is playable
6. **Producer owns the plan** — single source of truth for what to build next
