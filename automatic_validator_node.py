from data_moduels.agent_state import AgentState
from recipe_validator import LLMRecipeValidator
from shared_session_collector import session_collector

def automatic_validator_node(state: AgentState) -> AgentState:
    # Start node timing
    session_collector.start_node("validate", state["validation_mode"])
    error_messages = ''

    if not state.get("current_json_output"):
        return state

    validators = {
        "recipe": LLMRecipeValidator(),
    }

    validator = validators.get(state["domain"], LLMRecipeValidator())

    # Calculate quality metrics (jetzt ein Dict mit allen Metriken)
    quality_metrics = validator.calculate_quality_score(
        state["current_json_output"],
        recipe_name=state.get("recipe_name", "unknown")
    )

    print(f"Validator -> Iteration: {state['iteration_count']}")
    errors = validator.validate(state["current_json_output"], state["raw_text"])

    total_validation_cost = getattr(validator, 'last_validation_cost', 0)
    validation_input_tokens = getattr(validator, 'last_input_tokens', 0)
    validation_output_tokens = getattr(validator, 'last_output_tokens', 0)

    for error in errors:
        error_messages += "error_type: " + error.type + "; field_path: " + error.field_path + "; error_message: " + error.message + ""

    # Log to session collector mit allen Metriken
    session_collector.end_validation_node(
        quality_metrics=quality_metrics,  # Jetzt das komplette Dict
        cost=total_validation_cost,
        input_tokens=validation_input_tokens,
        output_tokens=validation_output_tokens,
        errors=error_messages
    )

    result = {
        **state,
        "validation_errors": errors,
        "quality_score": quality_metrics.get('overall_f1', 0.0),  # Für Kompatibilität
        "quality_metrics": quality_metrics  # Neue vollständige Metriken
    }

    return result