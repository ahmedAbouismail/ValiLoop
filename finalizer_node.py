from data_moduels.agent_state import AgentState
from shared_session_collector import session_collector

def finalizer_node(state: AgentState) -> AgentState:

    quality_score = state.get("quality_score", 0.0)
    success = quality_score > 0.8

    # Set final quality score in collector
    session_collector.set_final_quality_score(
        state["validation_mode"],
        quality_score
    )

    final_output = {
        "status": "success" if success else "partial_success",
        "data": state.get("current_json_output", {}),
        "quality_score": quality_score,
        "iterations_used": state["iteration_count"],
        "remaining_errors": [error.dict() for error in state.get("validation_errors", [])]
    }

    result = {
        **state,
        "final_output": final_output,
        "is_complete": True
    }

    return result