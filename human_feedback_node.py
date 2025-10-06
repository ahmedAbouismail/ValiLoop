import json
import time
from data_moduels.agent_state import AgentState
from gui.human_feedback_gui import launch_human_feedback_gui
from recipe_validator import LLMRecipeValidator
from shared_session_collector import session_collector

def human_feedback_node(state: AgentState) -> AgentState:
    # Start node timing
    session_collector.start_node("human_feedback", state["validation_mode"])

    validators = {
        "recipe": LLMRecipeValidator(),
    }

    validator = validators.get(state["domain"], LLMRecipeValidator())

    try:
        result = _gui_feedback(state)
        quality_score = validator.calculate_quality_score(
            state["current_json_output"],
            recipe_name=state.get("recipe_name", "unknown")
        )
    except Exception as e:
        print(f"GUI feedback failed: {e}")
        print("Falling back to console input...")
        result = _console_feedback(state)
        quality_score = validator.calculate_quality_score(
            state["current_json_output"],
            recipe_name=state.get("recipe_name", "unknown")
        )

    # Process the result
    if result['action'] == 'approve':
        is_approved = True
        feedback = result.get('feedback', None)
        feedback_type = "approval"
    else:  # 'correct'
        is_approved = False
        feedback = result.get('feedback', '')
        feedback_type = "correction"

    # End node timing
    session_collector.end_human_feedback_node(quality_score=quality_score)

    result_state = {
        **state,
        "human_feedback": feedback,
        "quality_score": quality_score,
        "is_complete": is_approved
    }

    return result_state


def _gui_feedback(state: AgentState) -> dict:
    print(f"\n=== LAUNCHING GUI FOR HUMAN REVIEW ===")
    print(f"Domain: {state['domain']}")
    print(f"Opening GUI window...")

    result = launch_human_feedback_gui(
        raw_text=state["text"],
        json_output=state.get("current_json_output", {}),
        domain=state['domain'],
        iteration=state["iteration_count"]
    )

    print(f"GUI feedback received: {result['action']}")
    if result.get('feedback'):
        print(f"Feedback length: {len(result['feedback'])} characters")

    return result


def _console_feedback(state: AgentState) -> dict:
    """Fallback console feedback (original implementation)"""
    print(f"\n=== HUMAN REVIEW REQUIRED ===")
    print(f"Domain: {state['domain']}")
    print(f"Current JSON Output:")
    print(json.dumps(state.get("current_json_output", {}), indent=2, ensure_ascii=False))

    # Measure human response time
    human_start_time = time.time()
    feedback = input("\nPlease provide feedback (or press Enter to approve): ")
    human_response_time = time.time() - human_start_time

    is_approved = not feedback.strip()
    action = "approve" if is_approved else "correct"

    return {
        'action': action,
        'feedback': feedback if feedback.strip() else None,
        'response_time': human_response_time
    }


def human_decision_function(state: AgentState) -> str:
    if state["iteration_count"] >= state["max_iterations"]:
        return "finalize"

    if state["is_complete"]:
        return "finalize"

    return "transform"