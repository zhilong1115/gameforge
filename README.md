# GameForge 🎮

AI Game Development Studio — takes a Game Design Document and builds a playable game using multi-agent AI.

## Architecture

- **LangGraph** — deterministic orchestration between milestones
- **AutoGen** — free-form multi-agent discussion within milestones
- **Human-in-the-loop** — milestone checkpoints for review & approval

See [ARCHITECTURE.md](ARCHITECTURE.md) for full design.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run with a GDD
gameforge run examples/hu/game_design.md
```

## Project Structure

```
gameforge/
├── src/gameforge/
│   ├── producer/        # GDD parser → milestone plan
│   ├── agents/          # AutoGen agents (designer, critic, coder, balancer)
│   ├── orchestrator/    # LangGraph workflow & state
│   ├── simulator/       # Game engine & playtesting
│   ├── translator/      # Execution plan → framework adapter
│   ├── eval/            # Metrics & reporting
│   ├── models/          # Pydantic data models
│   ├── tools/           # LLM & file I/O utilities
│   └── cli.py           # CLI entry point
├── tests/               # Unit & integration tests
├── examples/            # Example GDDs
│   └── hu/              # HU - Mahjong Roguelike
├── docs/                # Documentation
├── ARCHITECTURE.md      # System architecture
├── pyproject.toml       # Project config
└── README.md            # This file
```

## License

MIT
