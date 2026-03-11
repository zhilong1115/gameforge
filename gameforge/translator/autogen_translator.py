"""AutoGen Translator — converts ExecutionPlan to AutoGen GroupChat code.

THIS IS YOUR CODE TO WRITE, ZHILONG.

The Translator generates runnable Python files that use Microsoft AutoGen
to orchestrate the three agents (Designer, Implementer, Playtester) in a
free-form GroupChat conversation.

Key challenges:
- Agent creation: map AgentConfig → AutoGen AssistantAgent with correct system_message
- GroupChat setup: enable free-form communication (not round-robin)
- Tool binding: give agents the right tools (file I/O, git, browser, terminal)
- Milestone checking: after each Playtester turn, check if exit criteria are met
- Human gate: pause between milestones for human review
- Feedback routing: when Playtester says "BUG", next speaker should be Implementer
"""

from gameforge.models.plan import ExecutionPlan, Milestone, AgentConfig
from gameforge.translator.base import Translator, ProjectFiles


class AutoGenTranslator(Translator):
    """Generate AutoGen GroupChat code from an ExecutionPlan."""

    def translate(self, plan: ExecutionPlan) -> ProjectFiles:
        """Generate runnable AutoGen project files.
        
        TODO (Zhilong): Implement this.
        
        Suggested output files:
        - main.py: orchestrator that runs milestones sequentially
        - agents.py: agent definitions (Designer, Implementer, Playtester)
        - tools.py: tool functions (file_read, file_write, git_commit, run_tests, etc.)
        - milestone_checker.py: evaluates exit criteria after each Playtester turn
        - config.py: model settings, API keys, paths
        
        Architecture:
        
        main.py:
            for milestone in plan.milestones:
                print(f"Starting milestone: {milestone.name}")
                group_chat = create_group_chat(milestone, agents)
                run_chat(group_chat, max_rounds=milestone.max_iterations)
                
                if not milestone_met(milestone):
                    print("Milestone not met, escalating to human")
                    
                input("Human review — press Enter to proceed")  # Human gate
        
        agents.py:
            def create_agents(plan):
                designer = AssistantAgent(
                    name="Designer",
                    system_message=plan.agents["designer"].system_context,
                    llm_config={"model": plan.agents["designer"].model},
                )
                implementer = AssistantAgent(...)
                playtester = AssistantAgent(...)
                return [designer, implementer, playtester]
        
        GroupChat speaker selection:
            - Default: round-robin or auto (let AutoGen decide)
            - Override: if last message contains "BUG" → next speaker = Implementer
            - Override: if last message contains "BORING"/"TOO_HARD"/"TOO_EASY" → Designer
            - Override: if last message contains "PASS" → milestone check
        """
        raise NotImplementedError("AutoGenTranslator.translate() — your code goes here!")

    def _generate_main(self, plan: ExecutionPlan) -> str:
        """Generate main.py — the orchestrator.
        
        TODO (Zhilong): Implement.
        """
        raise NotImplementedError

    def _generate_agents(self, plan: ExecutionPlan) -> str:
        """Generate agents.py — agent definitions with system prompts.
        
        TODO (Zhilong): Implement.
        """
        raise NotImplementedError

    def _generate_tools(self, plan: ExecutionPlan) -> str:
        """Generate tools.py — tool functions for agents.
        
        Suggested tools:
        - file_read(path) → str
        - file_write(path, content) → bool
        - git_commit(message) → str
        - run_command(cmd) → str
        - run_tests() → str
        - browser_open(url) → str  (for UI playtesting)
        - batch_simulate(config, n_games) → dict  (for adapter playtesting)
        
        TODO (Zhilong): Implement.
        """
        raise NotImplementedError

    def _generate_milestone_checker(self, plan: ExecutionPlan) -> str:
        """Generate milestone_checker.py — exit criteria evaluator.
        
        TODO (Zhilong): Implement.
        """
        raise NotImplementedError

    def _generate_speaker_selection(self) -> str:
        """Generate custom speaker selection function for GroupChat.
        
        This is the feedback routing logic:
        - Playtester says BUG → next speaker = Implementer
        - Playtester says BORING/TOO_HARD/TOO_EASY → next speaker = Designer
        - Playtester says PASS → trigger milestone check
        - Otherwise → auto (let agents decide)
        
        TODO (Zhilong): Implement.
        """
        raise NotImplementedError
