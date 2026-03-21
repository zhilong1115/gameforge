"""GameForge Agent definitions.

Each agent has:
- AGENT_CONFIG: metadata (name, model, temperature, skills)
- SYSTEM_PROMPT: detailed instructions for the agent's role

Inspired by Claude Code Game Studios' agent hierarchy with
GameForge's LangGraph + AutoGen architecture.
"""

from gameforge.agents.producer import (
    AGENT_CONFIG as PRODUCER_CONFIG,
    SYSTEM_PROMPT as PRODUCER_PROMPT,
)
from gameforge.agents.designer import (
    AGENT_CONFIG as DESIGNER_CONFIG,
    SYSTEM_PROMPT as DESIGNER_PROMPT,
)
from gameforge.agents.critic import (
    AGENT_CONFIG as CRITIC_CONFIG,
    SYSTEM_PROMPT as CRITIC_PROMPT,
)
from gameforge.agents.coder import (
    AGENT_CONFIG as CODER_CONFIG,
    SYSTEM_PROMPT as CODER_PROMPT,
)
from gameforge.agents.balancer import (
    AGENT_CONFIG as BALANCER_CONFIG,
    SYSTEM_PROMPT as BALANCER_PROMPT,
)

AGENTS = {
    "producer": {"config": PRODUCER_CONFIG, "prompt": PRODUCER_PROMPT},
    "designer": {"config": DESIGNER_CONFIG, "prompt": DESIGNER_PROMPT},
    "critic": {"config": CRITIC_CONFIG, "prompt": CRITIC_PROMPT},
    "coder": {"config": CODER_CONFIG, "prompt": CODER_PROMPT},
    "balancer": {"config": BALANCER_CONFIG, "prompt": BALANCER_PROMPT},
}

__all__ = ["AGENTS"]
