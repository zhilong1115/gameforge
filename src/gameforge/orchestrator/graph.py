"""LangGraph workflow definition for GameForge."""

# TODO: Implement the full LangGraph workflow
# This is the skeleton — nodes will be added as agents are implemented.
#
# Graph structure:
#
# parse_gdd → plan_milestones → [milestone_loop]
#                                    ↓
#                              design_phase (AutoGen)
#                                    ↓
#                              code_phase (AutoGen)
#                                    ↓
#                              playtest_phase (algorithmic)
#                                    ↓
#                              balance_phase (AutoGen)
#                                    ↓
#                              check_playtest → pass? → human_review → next_milestone
#                                    ↓ fail
#                              back to design_phase
