from langgraph.constants import START, END
from langgraph.graph import StateGraph

from automatic_decision_function import automatic_decision_function
from automatic_validator_node import automatic_validator_node
from decision_node import decision_node
from finalizer_node import finalizer_node
from human_feedback_node import human_feedback_node, human_decision_function
from json_transformer_node import json_transformer_node
from data_moduels.agent_state import AgentState
from input_processor_node import input_processor_node

def create_json_processing_graph():

    # Initialize graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("input_processor", input_processor_node)
    workflow.add_node("transform", json_transformer_node)
    workflow.add_node("validate", automatic_validator_node)
    workflow.add_node("human_feedback", human_feedback_node)
    workflow.add_node("finalize", finalizer_node)

    # Add edges
    workflow.add_edge(START, "input_processor")
    workflow.add_edge("input_processor", "transform")
    # Add conditional edges
    workflow.add_conditional_edges(
        "transform",
        decision_node,
        {
            "validate": "validate",
            "human_feedback": "human_feedback",
            "finalize": "finalize"
        }
    )

    workflow.add_conditional_edges(
        "validate",
        automatic_decision_function,
        {
            "transform": "transform",
            "finalize": "finalize"
        }
    )

    workflow.add_conditional_edges(
        "human_feedback",
        human_decision_function,
        {
            "transform": "transform",
            "finalize": "finalize"
        }
    )

    workflow.add_edge("finalize", END)

    return workflow