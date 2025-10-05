from pydantic.v1 import BaseModel

from data_moduels.error_severity import ErrorSeverity


class ValidationError(BaseModel):
    class Config:
        use_enum_values = True
    type: str
    message: str
    severity: ErrorSeverity
    field_path: str
    suggested_fix: str = ""