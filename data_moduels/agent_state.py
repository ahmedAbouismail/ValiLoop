from typing import TypedDict, Dict, Any, Optional, List

from data_moduels.validation_error import ValidationError
from data_moduels.validation_mode import ValidationMode


class AgentState(TypedDict):
    # Input
    recipe_name: str
    raw_text: str
    text: str
    target_schema: Dict[str, Any]
    domain: str

    # Processing
    current_json_output: Optional[Dict[str, Any]]
    validation_errors: List[ValidationError]
    iteration_count: int
    max_iterations: int

    # Feedback
    human_feedback: Optional[str]
    validation_mode: ValidationMode

    # Results
    final_output: Optional[Dict[str, Any]]
    is_complete: bool
    quality_score: Optional[float]