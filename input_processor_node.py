from data_moduels.agent_state import AgentState

def input_processor_node(state: AgentState) -> AgentState:

    #processed_text = " ".join(state["raw_text"].split())
    processed_text = state["raw_text"]

    result = {
        **state,
        "raw_text": processed_text,
        "iteration_count": 0,
        "validation_errors": [],
        "is_complete": False
    }
    # result = {
    #     **state,
    #     "raw_text": processed_text,
    #     "iteration_count": 0,
    #     "validation_errors": [],
    #     "is_complete": False
    # }

    return result