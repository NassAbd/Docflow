from pydantic import BaseModel, Field

from app.schemas.document import DocumentType


class ClassificationResult(BaseModel):
    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0, description="Score de confiance entre 0 et 1")
    model_used: str
    raw_response: str | None = None
