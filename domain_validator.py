# === Domain Validators ===
from typing import Dict, List

from data_moduels.validation_error import ValidationError


class DomainValidator:
    def validate(self, json_output: Dict, raw_text: str) -> List[ValidationError]:
        raise NotImplementedError

    def calculate_quality_score(self, json_output: Dict) -> float:
        raise NotImplementedError
