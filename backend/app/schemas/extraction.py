import re
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class MonetaryAmount(BaseModel):
    ht: Decimal | None = None
    tva: Decimal | None = None
    ttc: Decimal | None = None
    currency: str = "EUR"


class ExtractedData(BaseModel):
    # Identifiants légaux
    siren: str | None = Field(None, description="Numéro SIREN (9 chiffres)")
    siret: str | None = Field(None, description="Numéro SIRET (14 chiffres)")

    # Parties
    emetteur_nom: str | None = None
    emetteur_adresse: str | None = None
    destinataire_nom: str | None = None
    destinataire_adresse: str | None = None

    # Montants
    montants: MonetaryAmount = Field(default_factory=MonetaryAmount)

    # Dates
    date_emission: str | None = None
    date_echeance: str | None = None

    # Référence document
    numero_document: str | None = None

    # Texte brut OCR
    raw_text: str = ""

    @field_validator("siren")
    @classmethod
    def validate_siren(cls, v: str | None) -> str | None:
        if v is not None and not re.fullmatch(r"\d{9}", v):
            raise ValueError(f"SIREN invalide : '{v}' doit contenir exactement 9 chiffres")
        return v

    @field_validator("siret")
    @classmethod
    def validate_siret(cls, v: str | None) -> str | None:
        if v is not None and not re.fullmatch(r"\d{14}", v):
            raise ValueError(f"SIRET invalide : '{v}' doit contenir exactement 14 chiffres")
        return v
