import json

from langchain_openai import ChatOpenAI

from data_moduels.agent_state import AgentState
from data_moduels.error_severity import ErrorSeverity
from data_moduels.validation_error import ValidationError
from shared_session_collector import session_collector
from utils.calculate_cost import calculate_openai_cost

def json_transformer_node(state: AgentState) -> AgentState:

    # Start node timing
    session_collector.start_node("transform", state["validation_mode"])

    schema_dict = state['target_schema']
    llm = ChatOpenAI(
        model="gpt-5-nano",
        #temperature=0.0,
        api_key="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"
    ).with_structured_output(schema=schema_dict, include_raw=True)
    #llm = llm_manager.get_transform_llm(state["validation_mode"]).with_structured_output(schema=schema_dict, include_raw=True)
    # Build prompt

    prompt = f"""
    Konvertieren Sie den folgenden Text gemäß dem Schema in das JSON-Format.
    
    Text: {state['raw_text']}
    Domain: {state['domain']}
    """

    if state['validation_mode'].value == 'automatic' and state['validation_errors'] and state['iteration_count'] > 0:

        prompt += f"\n\n=== WICHTIG: Beheben Sie diese spezifischen Fehler ===\n"
        ingredient_errors = [e for e in state['validation_errors'] if 'ingredients' in e.field_path]
        instruction_errors = [e for e in state['validation_errors'] if 'cooking_steps' in e.field_path]
        completeness_errors = [e for e in state['validation_errors'] if e.field_path in
                               ['completeness', 'cooking_steps', 'time', 'portions', 'name', 'ingredients']]

        if ingredient_errors:
            prompt += "\nZU KORRIGIERENDE FEHLER BEI DEN ZUTATEN:\n"
            for error in ingredient_errors:
                prompt += f"- {error.message}\n"
                if error.suggested_fix:
                    prompt += f"  → Korrigiere: {error.suggested_fix}\n"

        if instruction_errors:
            prompt += "\nZU KORRIGIERENDE FEHLER BEI DER ANWEISUNG:\n"
            for error in instruction_errors:
                prompt += f"- {error.message}\n"
                if error.suggested_fix:
                    prompt += f"  → Korrigiere: {error.suggested_fix}\n"

        if completeness_errors:
            prompt += "\nFEHLENDE INFORMATIONEN ZUM HINZUFÜGEN:\n"
            for error in completeness_errors:
                prompt += f"- {error.message}\n"
                if error.suggested_fix:
                    prompt += f"  → HINZUFÜGE: {error.suggested_fix}\n"
        # for error in state['validation_errors']:
        #     prompt += f"- {error.message}\n"
        #     if error.suggested_fix:
        #         prompt += f"  → Korrigiere: {error.suggested_fix}\n"

    if state['validation_mode'].value == 'human' and state['iteration_count'] > 0:
        prompt += f"\n\n=== FEEDBACK ===\n{state['human_feedback']}\n"

    if state['domain'] == 'recipe':
        prompt += """
        \nWICHTIG:
            - Nutze nur wörtliche Belege aus dem ORIGINALTEXT.
            - Extrahieren Sie alle Zutaten mit ihren genauen Mengenangaben und Einheiten, **sofern im Originaltext angegeben**.
            - Wenn für eine Zutat keine Menge oder Einheit vorhanden ist, lassen Sie die Felder "menge" und "einheit" leer, oder setzen Sie sie auf null oder einen geeigneten Platzhalter. **Erfinden Sie keine Werte**.
            - Extrahieren Sie alle Kochschritte klar und logisch.
            - Geben Sie Kochzeiten und Temperaturen an, sofern sie im Text erwähnt sind.
            - Stellen Sie sicher, dass jede Zutat in der Anweisung verwendet wird.
            - Nutze nur wörtliche Belege aus dem ORIGINALTEXT.
        """

    try:
        print(f"Calling the transformer")
        response = llm.invoke(prompt)
        print(f"Transformer returned the result")

        parsed_response = response["parsed"]
        token_usage = response["raw"].usage_metadata
        cost = calculate_openai_cost(token_usage or {}, "gpt-5-nano")

        # Log to session collector
        session_collector.end_transform_node(
            cost=cost,
            input_tokens=(token_usage or {}).get('input_tokens', 0),
            output_tokens=(token_usage or {}).get('output_tokens', 0)
        )

        result = {
            **state,
            "current_json_output": parsed_response,
            "iteration_count": state["iteration_count"] + 1
        }

        return result

    except json.JSONDecodeError as e:
        error = ValidationError(
            type="json_parse_error",
            message=f"Failed to parse JSON from LLM response: {str(e)}",
            severity=ErrorSeverity.CRITICAL,
            field_path="root",
            suggested_fix="Ensure the response is valid JSON format"
        )

        result = {
            **state,
            "validation_errors": [error],
            "iteration_count": state["iteration_count"] + 1
        }

        return result