from data_moduels.agent_state import AgentState

def automatic_decision_function(state: AgentState) -> str:
    # Check iteration limit
    if state["iteration_count"] >= state["max_iterations"]:
        return "finalize"

    # If there are errors, retry
    if state["validation_errors"]:
        return "transform"

    return "finalize"