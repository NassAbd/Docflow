from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class AlertType(StrEnum):
    SIRET_MISMATCH = "siret_mismatch"
    AMOUNT_INCONSISTENCY = "amount_inconsistency"
    DATE_INCOHERENCE = "date_incoherence"
    SIREN_FORMAT_INVALID = "siren_format_invalid"


class AlertSeverity(StrEnum):
    CRITIQUE = "critique"
    HAUTE = "haute"
    MOYENNE = "moyenne"
    FAIBLE = "faible"


class InconsistencyAlert(BaseModel):
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    description: str
    document_ids: list[UUID] = Field(default_factory=list)
    field_in_conflict: str | None = None
    value_a: str | None = None
    value_b: str | None = None
    suggestion: str | None = None
