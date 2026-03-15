from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.classification import ClassificationResult
from app.schemas.document import DocumentType, UploadedDocument
from app.schemas.extraction import ExtractedData
from app.schemas.fraud import InconsistencyAlert


class BronzeRecord(BaseModel):
    """Zone Bronze : fichier brut uploadé, aucun traitement."""
    document: UploadedDocument
    file_path: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


class SilverRecord(BaseModel):
    """Zone Silver : données extraites et normalisées."""
    document_id: UUID
    original_filename: str
    document_type: DocumentType
    classification: ClassificationResult
    extraction: ExtractedData
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class GoldRecord(BaseModel):
    """Zone Gold : données curées, enrichies, prêtes pour les apps métiers."""
    document_id: UUID
    original_filename: str
    document_type: DocumentType
    extraction: ExtractedData
    alerts: list[InconsistencyAlert] = Field(default_factory=list)
    is_compliant: bool = True
    curated_at: datetime = Field(default_factory=datetime.utcnow)


class DataLakeManifest(BaseModel):
    """Index de chaque zone du Data Lake."""
    zone: str  # bronze | silver | gold
    records: list[str] = Field(default_factory=list)  # liste d'IDs de documents
    last_updated: datetime = Field(default_factory=datetime.utcnow)
