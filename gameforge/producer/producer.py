"""Producer Agent — reads game_design.md and generates execution_plan.json.

THIS IS YOUR CODE TO WRITE, ZHILONG.

The Producer is the "brain" of GameForge:
1. Read a game design document (markdown)
2. Analyze the scope — what systems, tech stack, complexity
3. Decide adapter_needed — does this game need statistical balancing?
4. Decompose into milestones with clear exit criteria
5. Configure agents with appropriate system contexts
6. Output a validated ExecutionPlan

Key challenges:
- LLM structured output: getting the model to produce valid ExecutionPlan JSON
- Prompt design: the prompt must work for ANY game genre, not just HU
- Validation: handle malformed LLM output gracefully (retry, fix, fallback)
- Milestone ordering: dependencies between milestones must be logical
"""

from pathlib import Path

from gameforge.models.plan import ExecutionPlan
from gameforge.tools.llm import LLMClient


class Producer:
    """Generates an ExecutionPlan from a game design document."""

    def __init__(self, llm: LLMClient, model: str = "claude-opus-4-6"):
        self.llm = llm
        self.model = model

    def generate_plan(self, game_design_path: str | Path) -> ExecutionPlan:
        """Read game_design.md and produce an ExecutionPlan.
        
        Args:
            game_design_path: Path to the game design markdown file.
            
        Returns:
            A validated ExecutionPlan ready for the Translator.
            
        Raises:
            ValueError: If the LLM output cannot be parsed into a valid plan.
        """
        game_design = Path(game_design_path).read_text()

        # TODO (Zhilong): Implement this
        #
        # Suggested approach:
        # 1. Build a system prompt that explains what an ExecutionPlan is
        #    (include the JSON schema from ExecutionPlan.model_json_schema())
        # 2. Send game_design as the user message
        # 3. Parse the LLM response as JSON → ExecutionPlan
        # 4. Validate: milestones make sense, agents have system_context, etc.
        # 5. Handle failures: retry with error feedback, or raise
        #
        # Hints:
        # - ExecutionPlan.model_json_schema() gives you the full JSON schema
        # - Use self.llm.complete() to call the LLM
        # - Consider using response_format={"type": "json_object"} if supported
        # - The prompt should work for ANY game, not just HU
        
        raise NotImplementedError("Producer.generate_plan() — your code goes here!")

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the Producer LLM call.
        
        TODO (Zhilong): Design this prompt.
        
        The prompt should:
        - Explain the Producer's role
        - Include the ExecutionPlan JSON schema
        - Give examples of good milestone decomposition
        - Explain when adapter_needed should be true
        - Instruct the LLM to output ONLY valid JSON
        """
        schema = ExecutionPlan.model_json_schema()
        
        raise NotImplementedError("Producer._build_system_prompt() — your code goes here!")

    def _validate_plan(self, plan: ExecutionPlan) -> list[str]:
        """Validate an execution plan for logical consistency.
        
        TODO (Zhilong): Implement validation rules.
        
        Suggested checks:
        - At least 2 milestones
        - All 3 agent roles present in agents dict
        - If adapter_needed, at least one milestone has adapter_hint
        - Exit criteria are non-empty for each milestone
        - Milestone IDs are sequential
        - System contexts are substantive (not empty/generic)
        
        Returns:
            List of validation error strings. Empty = valid.
        """
        raise NotImplementedError("Producer._validate_plan() — your code goes here!")
