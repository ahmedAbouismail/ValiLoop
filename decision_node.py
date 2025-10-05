from data_moduels.agent_state import AgentState
from data_moduels.validation_mode import ValidationMode

def decision_node(state: AgentState) -> str:

    # Check iteration limit
    if state["iteration_count"] > state["max_iterations"]:
        return "finalize"

    if state["validation_mode"] == ValidationMode.HUMAN:
        return "human_feedback"

    # If there are errors, retry
    if state["validation_mode"] == ValidationMode.AUTOMATIC:
        return "validate"