import json
from typing import Dict, List

from langchain_openai import ChatOpenAI

from data_moduels.error_severity import ErrorSeverity
from data_moduels.validation_error import ValidationError
from domain_validator import DomainValidator
from llm_manager import llm_manager
from utils.calculate_cost import calculate_openai_cost
from difflib import SequenceMatcher
import json
import os


class LLMRecipeValidator(DomainValidator):
    def __init__(self):
        #self.llm = llm_manager.get_validation_llm()
        self.llm = ChatOpenAI(
            model="gpt-5-nano",
            temperature=0.0,
            api_key="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"
        )
        self.last_validation_cost = 0  # Für Monitoring

    def validate(self, json_output: Dict, raw_text: str) -> List[ValidationError]:
        errors = []
        total_cost = 0
        total_input_tokens = 0
        total_output_tokens = 0

        # 1. Validiere Zutaten
        print(f"Validating ingredients with LLM")
        ingredient_errors, cost1, input1, output1 = self._validate_ingredients_with_llm(json_output, raw_text)
        errors.extend(ingredient_errors)
        total_cost += cost1
        total_input_tokens += input1
        total_output_tokens += output1

    # 2. Validiere kochschritte
        print(f"Validating instructions with LLM")
        instruction_errors, cost2, input2, output2 = self._validate_instructions_with_llm(json_output, raw_text)
        errors.extend(instruction_errors)
        total_cost += cost2
        total_input_tokens += input2
        total_output_tokens += output2

        # 3. Validiere Vollständigkeit
        print(f"Validating completeness with LLM")
        completeness_errors, cost3, input3, output3 = self._validate_completeness_with_llm(json_output, raw_text)
        errors.extend(completeness_errors)
        total_cost += cost3
        total_input_tokens += input3
        total_output_tokens += output3

        # Store total cost for monitoring
        self.last_validation_cost = total_cost
        self.last_input_tokens = total_input_tokens
        self.last_output_tokens = total_output_tokens

        return errors
    def _validate_ingredients_with_llm(self, json_output: Dict, raw_text: str) -> tuple[List[ValidationError], float, int, int]:

        extracted_ingredients = json_output.get('ingredients', [])

        # Structured-Output-Schema (top-level Objekt mit 'errors'-Array)
        with open('assets/validation_schemas/ingredients_validation_schema.json', 'r', encoding='utf-8') as f:
            schema = json.load(f)

        prompt = f"""
                    Rolle
                    Du prüfst ausschließlich die Felder ZUTAT (name), MENGE (quantity) und EINHEIT (unit) der EXTRAKTION gegen den ORIGINALTEXT. 
                    Alles andere ignorierst du.
                    
                    Belege
                    - Nutze nur wörtliche Belege aus dem ORIGINALTEXT.
                    - Keine Vermutungen, kein Weltwissen, keine Umrechnungen oder Synonyme.
                    - Behandle Umlaute (ä, ö, ü, ß) und ihre alternativen Schreibweisen (ae, oe, ue, ss) als identisch.
                    
                    Null-Regeln
                    - quantity = Null ist nur dann korrekt, wenn im ORIGINALTEXT keine Menge genannt ist.
                    - unit = Null ist nur dann korrekt, wenn im ORIGINALTEXT keine Einheit genannt ist.
                    
                    Fehlertypen
                    - omission: Im ORIGINALTEXT vorhanden, in der EXTRAKTION fehlt es.
                    - unsupported: In der EXTRAKTION steht etwas, das der ORIGINALTEXT nicht stützt (falsch oder erfunden).
                    
                    Scope
                    - ingredient: betrifft die ganze Zutat (z. B. Zutat fehlt).
                    - value: betrifft ein Feld (z. B. Menge/Einheit falsch oder fehlt).
                    
                    Vorgehen
                    1) Für jede Zutat der EXTRAKTION name, quantity, unit gegen den ORIGINALTEXT prüfen.
                    2) Abweichungen als unsupported (scope: value) markieren.
                    3) Falls im Text eine Menge/Einheit existiert, in der EXTRAKTION aber Null ist → omission (scope: value).
                    4) Zutaten, die im ORIGINALTEXT vorkommen, in der EXTRAKTION aber komplett fehlen → omission (scope: ingredient).
                    
                    Ausgabe (nur JSON, keine Zusatztexte)
                    - Gib exakt dieses Format aus:
                    {{
                        "error": [
                        {{
                            "error_type": "omission" | "unsupported",
                            "scope": "ingredient" | "value",
                            "field_path": "z. B. ingredients[2].quantity",
                            "message": "kurze, belegte Begründung mit Wortlaut aus dem Text",
                            "recommended_fix": "konkrete Korrektur, direkt aus dem Text ableitbar"
                        }}
                      ]
                    }}
                    
                    - Wenn es **keine** Fehler gibt, gib **genau** dies aus:
                    {{ "error": [] }}

                    ---
                    **ORIGINALTEXT:**
                    {raw_text}
                    ---
                    **EXTRAHIERTE ZUTATEN:**
                    {json.dumps(extracted_ingredients, indent=2, ensure_ascii=False)}
                    ---
                """

        try:
            validator = self.llm.with_structured_output(schema=schema, include_raw=True)

            response = validator.invoke(prompt)
            parsed_response = response["parsed"]
            token_usage = response["raw"].usage_metadata

            # response ist ein Dict: {"errors": [ ... ]}
            items = parsed_response.get("error", []) if isinstance(parsed_response, dict) else []
            errors = [self._create_validation_error(item, "ingredients") for item in items]

            input_tokens = token_usage.get('input_tokens', 0) if token_usage else 0
            output_tokens = token_usage.get('output_tokens', 0) if token_usage else 0
            cost = calculate_openai_cost(token_usage, "gpt-5-nano")

            return errors, cost, input_tokens, output_tokens

        except Exception as e:
            err = ValidationError(
                type="llm_validation_error",
                message=f"LLM-Validierung fehlgeschlagen: {str(e)}",
                severity=ErrorSeverity.MINOR,
                field_path="ingredients"
            )
            return [err], 0.0, 0, 0

    def _validate_instructions_with_llm(self, json_output: Dict, raw_text: str) -> tuple[List[ValidationError], float, int, int]:

        extracted_instructions = json_output.get('cooking_steps', [])

        with open('assets/validation_schemas/instructions_validation_schema.json', 'r', encoding='utf-8') as f:
            schema = json.load(f)

        prompt = f"""
                    Rolle
                    Du prüfst ausschließlich das Feld cooking_steps der EXTRAKTION gegen den ORIGINALTEXT. 
                    Alles andere ignorierst du.
                
                    Belege
                    - Nutze nur wörtliche Belege aus dem ORIGINALTEXT.
                    - Keine Vermutungen, kein Weltwissen, keine Umrechnungen oder Synonyme.
                    - Behandle Umlaute (ä, ö, ü, ß) und ihre alternativen Schreibweisen (ae, oe, ue, ss) als identisch.
                
                    Fehlertypen
                    - omission: Im ORIGINALTEXT vorhanden, in der EXTRAKTION fehlt es.
                    - wrong_order: Im ORIGINALTEXT vorhanden aber in einer anderen Reihenfoglge
                    - unsupported: In der EXTRAKTION steht etwas, das der ORIGINALTEXT nicht stützt (falsch oder erfunden).
                
                    Vorgehen
                    1) Für jeden Schritt der EXTRAKTION gegen den ORIGINALTEXT prüfen.
                    2) Title, die im ORIGINALTEXT vorkommen, in der EXTRAKTION aber komplett fehlen → omission
                    3) Title, die in der EXTRAKTION vorkommen, im ORIGINALTEXT aber komplett fehlen → unsupported
                    4) Schritte, die im ORIGINALTEXT vorkommen, in der EXTRAKTION aber komplett fehlen → omission
                    5) Schritte, die im ORIGINALTEXT und im EXTRAKTION aber in einer anderen Reihenfolge vorkommen -> wrong_order
                
                    Ausgabe (nur JSON, keine Schritttexte)
                    - Gib exakt dieses Format aus:
                    {{
                        "error": [
                        {{
                            "error_type": "omission" | "wrong_order" | "unsupported",
                            "field_path": "z. B. cooking_steps[2].sub_steps[1]",
                            "message": "kurze, belegte Begründung mit Wortlaut aus dem Text",
                            "recommended_fix": "konkrete Korrektur, direkt aus dem Text ableitbar"
                        }}
                      ]
                    }}
                    
                    - Wenn es **keine** Fehler gibt, gib **genau** dies aus:
                    {{ "error": [] }}
                
                    ---
                    **ORIGINALTEXT:**
                    {raw_text}
                    ---
                    **EXTRAHIERTE Kochschritte:**
                    {json.dumps(extracted_instructions, indent=2, ensure_ascii=False)}
                    ---
                """
        try:
            validator = self.llm.with_structured_output(schema=schema, include_raw=True)
            response = validator.invoke(prompt)
            parsed_response = response["parsed"]
            token_usage = response["raw"].usage_metadata

            items = parsed_response.get("error", []) if isinstance(parsed_response, dict) else []
            errors = [self._create_validation_error(item, "cooking_steps") for item in items]

            input_tokens = token_usage.get('input_tokens', 0) if token_usage else 0
            output_tokens = token_usage.get('output_tokens', 0) if token_usage else 0
            cost = calculate_openai_cost(token_usage, "gpt-5-nano")

            return errors, cost, input_tokens, output_tokens

        except Exception as e:
            err = ValidationError(
                type="llm_validation_error",
                message=f"LLM-Validierung fehlgeschlagen: {str(e)}",
                severity=ErrorSeverity.MINOR,
                field_path="instructions"
            )
            return [err], 0.0, 0, 0
    def _validate_completeness_with_llm(self, json_output: Dict, raw_text: str) -> tuple[List[ValidationError], float, int, int]:

        with open('assets/validation_schemas/completeness_validation_schema.json', 'r', encoding='utf-8') as f:
            schema = json.load(f)

        prompt = f"""
                    Du bist ein Kochexperte. Prüfe ob diese JSON-Extraktion vollständig ist.
    
                    ORIGINALTEXT:
                    {raw_text}
    
                    EXTRAHIERTE JSON:
                    {json.dumps(json_output, indent=2, ensure_ascii=False)}
    
                    PRÜFE VOLLSTÄNDIGKEIT:
                    1. Fehlen wichtige Informationen aus dem Originaltext?
                    2. Sind Portionsangaben, Kochzeiten, Temperaturen erfasst?
                    3. Ist der Rezeptname korrekt?
                    4. Wurden alle erwähnten Zubereitungschritte erfasst?
    
                    Gib ausschließlich ein JSON-Objekt gemäß Schema zurück. Wenn alles vollständig ist, gib {{"errors": []}} zurück.
                """

        try:
            validator = self.llm.with_structured_output(schema=schema, include_raw=True)
            response = validator.invoke(prompt)
            parsed_response = response["parsed"]
            token_usage = response["raw"].usage_metadata

            items = parsed_response.get("error", []) if isinstance(parsed_response, dict) else []
            errors = [self._create_validation_error(item, "completeness") for item in items]

            input_tokens = token_usage.get('input_tokens', 0) if token_usage else 0
            output_tokens = token_usage.get('output_tokens', 0) if token_usage else 0
            cost = calculate_openai_cost(token_usage, "gpt-5-nano")

            return errors, cost, input_tokens, output_tokens

        except Exception as e:
            err = ValidationError(
                type="llm_validation_error",
                message=f"LLM-Validierung fehlgeschlagen: {str(e)}",
                severity=ErrorSeverity.MINOR,
                field_path="completeness"
            )
            return [err], 0.0, 0, 0
    def _create_validation_error(self, error_data: dict, validation_type: str) -> ValidationError:

        severity_mapping = {
            'omission': ErrorSeverity.CRITICAL,
            'hallucination': ErrorSeverity.CRITICAL,
            'unsupported': ErrorSeverity.CRITICAL,
            'wrong_order': ErrorSeverity.CRITICAL,
        }

        error_type = error_data.get('error_type', 'unknown_error')
        severity = severity_mapping.get(error_type, ErrorSeverity.MINOR)

        return ValidationError(
            type=error_type,
            message=error_data.get('message', 'LLM-Validierungsfehler'),
            severity=severity,
            field_path=error_data.get('field_path', validation_type),
            suggested_fix=error_data.get('recommended_fix', '')
        )

    def calculate_quality_score(self, json_output: Dict, recipe_name: str = None) -> float:

        gold_standard = self._load_gold_standard(recipe_name)

        # Gewichtung der Felder nach Wichtigkeit
        field_weights = {
            'name': 0.1,           # 10% - Titel ist wichtig
            'ingredients': 0.4,    # 40% - Zutaten sind sehr wichtig
            'cooking_steps': 0.4,  # 40% - Schritte sind sehr wichtig
            'portions': 0.05,      # 5% - Nice to have
            'time': 0.05          # 5% - Nice to have
        }

        total_score = 0.0
        total_weight = 0.0

        # Bewerte jedes Feld
        for field, weight in field_weights.items():
            if field in gold_standard:
                total_weight += weight

                if field not in json_output:
                    # Feld fehlt komplett = 0 Punkte
                    field_score = 0.0
                elif field == 'ingredients':
                    # Spezielle Bewertung für Zutaten-Array
                    field_score = self._score_ingredients(gold_standard[field], json_output[field])
                elif field == 'cooking_steps':
                    # Spezielle Bewertung für Schritte-Array
                    field_score = self._score_cooking_steps(gold_standard[field], json_output[field])
                else:
                    # Einfache Felder: exakt gleich = 1.0, sonst 0.0
                    field_score = 1.0 if gold_standard[field] == json_output[field] else 0.0

                total_score += field_score * weight

        # Strafe für zusätzliche Felder die nicht im Gold-Standard sind
        extra_fields = set(json_output.keys()) - set(gold_standard.keys())
        penalty = len(extra_fields) * 0.05  # 5% Strafe pro zusätzlichem Feld

        final_score = (total_score / total_weight) if total_weight > 0 else 0.0
        final_score = max(0.0, final_score - penalty)

        print(f"Quality_score: {final_score}")

        return final_score
    def _load_gold_standard(self, recipe_name: str) -> Dict:
        filename = f"{recipe_name.replace(' ', '_')}.json"
        filepath = os.path.join("assets", "gold_standards", filename)

        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass

        return None

    # def _score_ingredients(self, gold_ingredients: list, current_ingredients: list) -> float:
    #     if not gold_ingredients:
    #         return 1.0 if not current_ingredients else 0.0
    #
    #     if not current_ingredients:
    #         return 0.0
    #
    #     # Liste der bereits verwendeten Indizes
    #     used_indices = set()
    #     correct_count = 0
    #
    #     # Für jede Gold-Zutat finde beste Übereinstimmung
    #     for gold_ingredient in gold_ingredients:
    #         best_match_found = False
    #
    #         # Suche in allen noch nicht verwendeten aktuellen Zutaten
    #         for i, current_ingredient in enumerate(current_ingredients):
    #             if i not in used_indices:  # Nur unverwendete prüfen
    #                 if self._ingredients_match(gold_ingredient, current_ingredient):
    #                     correct_count += 1
    #                     used_indices.add(i)  # Markiere als verwendet
    #                     best_match_found = True
    #                     break  # Stoppe bei erstem Match
    #
    #     # Score: gefundene Matches / erwartete Zutaten
    #     base_score = correct_count / len(gold_ingredients)
    #
    #     # Strafe für zusätzliche Zutaten (nicht gematcht)
    #     extra_ingredients = len(current_ingredients) - len(used_indices)
    #     if extra_ingredients > 0:
    #         penalty = extra_ingredients * 0.1
    #         base_score = max(0.0, base_score - penalty)
    #
    #     return base_score
    def _score_cooking_steps(self, gold_steps: list, current_steps: list) -> float:
        if not gold_steps:
            return 1.0 if not current_steps else 0.0

        if not current_steps:
            return 0.0

        used_indices = set()
        correct_count = 0

        # Für jeden Gold-Schritt finde besten Match
        for gold_step in gold_steps:
            for i, current_step in enumerate(current_steps):
                if i not in used_indices:
                    if self._steps_match(gold_step, current_step):
                        correct_count += 1
                        used_indices.add(i)
                        break

        return correct_count / len(gold_steps)

    def _steps_match(self, gold_step, current_step) -> bool:
        # Gold step ist String (altes Format)
        if isinstance(gold_step, str):
            gold_text = gold_step.lower()
        else:
            # Gold step ist Objekt (neues Format)
            gold_text = ""
            if isinstance(gold_step, dict):
                # Title sicher handhaben (kann None sein)
                if gold_step.get('title'):
                    gold_text += gold_step['title'].lower() + " "
                # Sub_steps sicher handhaben (kann None oder leere Liste sein)
                if gold_step.get('sub_steps') and isinstance(gold_step['sub_steps'], list):
                    # Filtere None-Werte aus sub_steps
                    valid_substeps = [step for step in gold_step['sub_steps'] if step is not None]
                    gold_text += " ".join(valid_substeps).lower()
            else:
                return False

        # Current step ist String (altes Format)
        if isinstance(current_step, str):
            current_text = current_step.lower()
        else:
            # Current step ist Objekt (neues Format)
            current_text = ""
            if isinstance(current_step, dict):
                # Title sicher handhaben (kann None sein)
                if current_step.get('title'):
                    current_text += current_step['title'].lower() + " "
                # Sub_steps sicher handhaben (kann None oder leere Liste sein)
                if current_step.get('sub_steps') and isinstance(current_step['sub_steps'], list):
                    # Filtere None-Werte aus sub_steps
                    valid_substeps = [step for step in current_step['sub_steps'] if step is not None]
                    current_text += " ".join(valid_substeps).lower()
            else:
                return False

        # Verhindere Vergleich von leeren Strings
        if not gold_text.strip() or not current_text.strip():
            return False

        similarity = SequenceMatcher(None, gold_text.strip(), current_text.strip()).ratio()
        return similarity > 0.8  # 80% Ähnlichkeit

    # def _score_cooking_steps(self, gold_steps: list, current_steps: list) -> float:
    #     if not gold_steps:
    #         return 1.0 if not current_steps else 0.0
    #
    #     if not current_steps:
    #         return 0.0
    #
    #     used_indices = set()
    #     correct_count = 0
    #
    #     # Für jeden Gold-Schritt finde besten Match
    #     for gold_step in gold_steps:
    #         for i, current_step in enumerate(current_steps):
    #             if i not in used_indices:
    #                 if self._steps_match(gold_step, current_step):
    #                     correct_count += 1
    #                     used_indices.add(i)
    #                     break
    #
    #     return correct_count / len(gold_steps)
    #
    # def _steps_match(self, gold_step: str, current_step: str) -> bool:
    #
    #     similarity = SequenceMatcher(None, gold_step.lower(), current_step.lower()).ratio()
    #     return similarity > 0.8  # 80% Ähnlichkeit

    def _score_ingredients(self, gold_ingredients: list, current_ingredients: list) -> float:
        if not gold_ingredients:
            return 1.0 if not current_ingredients else 0.0

        if not current_ingredients:
            return 0.0

        # Liste der bereits verwendeten Indizes
        used_indices = set()
        correct_count = 0

        # Für jede Gold-Zutat finde beste Übereinstimmung
        for gold_ingredient in gold_ingredients:
            best_match_found = False

            # Suche in allen noch nicht verwendeten aktuellen Zutaten
            for i, current_ingredient in enumerate(current_ingredients):
                if i not in used_indices:  # Nur unverwendete prüfen
                    if self._ingredients_match(gold_ingredient, current_ingredient):
                        correct_count += 1
                        used_indices.add(i)  # Markiere als verwendet
                        best_match_found = True
                        break  # Stoppe bei erstem Match

        # Score: gefundene Matches / erwartete Zutaten
        base_score = correct_count / len(gold_ingredients)

        # Strafe für zusätzliche Zutaten (nicht gematcht)
        extra_ingredients = len(current_ingredients) - len(used_indices)
        if extra_ingredients > 0:
            penalty = extra_ingredients * 0.1
            base_score = max(0.0, base_score - penalty)

        return base_score
    def _ingredients_match(self, gold_ingredient: dict, current_ingredient: dict) -> bool:
        if not isinstance(gold_ingredient, dict) or not isinstance(current_ingredient, dict):
            return False
        # Name mit SequenceMatcher vergleichen (wichtigster Teil)
        gold_name = gold_ingredient.get('name', '').lower()
        current_name = current_ingredient.get('name', '').lower()

        name_similarity = SequenceMatcher(None, gold_name, current_name).ratio()
        if name_similarity < 0.8:  # 80% Ähnlichkeit erforderlich
            return False

        # Quantity und Unit sind optional, aber wenn vorhanden sollten sie stimmen
        gold_qty = gold_ingredient.get('quantity')
        current_qty = current_ingredient.get('quantity')

        if gold_qty and current_qty and gold_qty != current_qty:
            return False

        gold_unit = gold_ingredient.get('unit')
        current_unit = current_ingredient.get('unit')

        if gold_unit and current_unit and gold_unit != current_unit:
            return False

        return True
    # def _ingredients_match(self, gold_ingredient: dict, current_ingredient: dict) -> bool:
    #     if not isinstance(gold_ingredient, dict) or not isinstance(current_ingredient, dict):
    #         return False
    #
    #     # Name muss übereinstimmen (wichtigster Teil)
    #     if gold_ingredient.get('name', '').lower() != current_ingredient.get('name', '').lower():
    #         return False
    #
    #     # Quantity und Unit sind optional, aber wenn vorhanden sollten sie stimmen
    #     gold_qty = gold_ingredient.get('quantity')
    #     current_qty = current_ingredient.get('quantity')
    #
    #     if gold_qty and current_qty and gold_qty != current_qty:
    #         return False
    #
    #     gold_unit = gold_ingredient.get('unit')
    #     current_unit = current_ingredient.get('unit')
    #
    #     if gold_unit and current_unit and gold_unit != current_unit:
    #         return False
    #
    #     return True