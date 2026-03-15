"""Tests TDD pour le service de détection de fraudes."""
import uuid
from decimal import Decimal

from app.schemas.classification import ClassificationResult
from app.schemas.datalake import SilverRecord
from app.schemas.document import DocumentType
from app.schemas.extraction import ExtractedData, MonetaryAmount
from app.schemas.fraud import AlertSeverity, AlertType
from app.services.fraud import detect_inconsistencies

# ─── Fixtures ────────────────────────────────────────────────────────────────

def make_silver(
    doc_type: DocumentType,
    siren: str | None = "123456789",
    siret: str | None = "12345678901234",
    emetteur_nom: str | None = "Acme SARL",
    montant_ttc: Decimal | None = None,
    date_emission: str | None = None,
) -> SilverRecord:
    return SilverRecord(
        document_id=uuid.uuid4(),
        original_filename=f"{doc_type.value}_test.pdf",
        document_type=doc_type,
        classification=ClassificationResult(
            document_type=doc_type,
            confidence=0.9,
            model_used="test-model",
        ),
        extraction=ExtractedData(
            siren=siren,
            siret=siret,
            emetteur_nom=emetteur_nom,
            montants=MonetaryAmount(ttc=montant_ttc),
            date_emission=date_emission,
            raw_text="texte test",
        ),
    )


# ─── Règle 1 : SIREN format ──────────────────────────────────────────────────

def test_no_alert_when_siren_valid():
    records = [make_silver(DocumentType.FACTURE, siren="123456789")]
    alerts = detect_inconsistencies(records)
    siren_alerts = [a for a in alerts if a.alert_type == AlertType.SIREN_FORMAT_INVALID]
    assert len(siren_alerts) == 0


def test_alert_when_siren_too_short():
    """
    Un SIREN invalide doit générer une alerte.
    On utilise model_construct() pour bypasser Pydantic et simuler des données
    corrompues (ex: lues depuis le filesystem ou issues d'un LLM mal formé).
    """
    bad_extraction = ExtractedData.model_construct(
        siren="12345",  # invalide — 5 chiffres au lieu de 9
        siret="12345678901234",
        emetteur_nom="Acme SARL",
        montants=MonetaryAmount(),
        raw_text="texte corrompu",
    )
    record = make_silver(DocumentType.FACTURE)
    record.extraction = bad_extraction

    alerts = detect_inconsistencies([record])
    siren_alerts = [a for a in alerts if a.alert_type == AlertType.SIREN_FORMAT_INVALID]
    assert len(siren_alerts) == 1
    assert siren_alerts[0].severity == AlertSeverity.HAUTE


# ─── Règle 2 : SIRET mismatch ────────────────────────────────────────────────

def test_no_alert_when_siret_identical():
    rec1 = make_silver(DocumentType.FACTURE, siret="12345678901234", emetteur_nom="Acme SARL")
    rec2 = make_silver(DocumentType.ATTESTATION, siret="12345678901234", emetteur_nom="Acme SARL")
    alerts = detect_inconsistencies([rec1, rec2])
    siret_alerts = [a for a in alerts if a.alert_type == AlertType.SIRET_MISMATCH]
    assert len(siret_alerts) == 0


def test_alert_when_siret_mismatch():
    rec1 = make_silver(DocumentType.FACTURE, siret="12345678901234", emetteur_nom="Acme SARL")
    rec2 = make_silver(DocumentType.ATTESTATION, siret="98765432109876", emetteur_nom="Acme SARL")
    alerts = detect_inconsistencies([rec1, rec2])
    siret_alerts = [a for a in alerts if a.alert_type == AlertType.SIRET_MISMATCH]
    assert len(siret_alerts) == 1
    assert siret_alerts[0].severity == AlertSeverity.CRITIQUE
    all_values = {siret_alerts[0].value_a, siret_alerts[0].value_b}
    assert "12345678901234" in all_values
    assert "98765432109876" in all_values


# ─── Règle 3 : Montant incohérent ────────────────────────────────────────────

def test_no_alert_when_amounts_within_tolerance():
    devis = make_silver(DocumentType.DEVIS, montant_ttc=Decimal("1000.00"), emetteur_nom="Acme")
    facture = make_silver(DocumentType.FACTURE, montant_ttc=Decimal("1040.00"), emetteur_nom="Acme")
    alerts = detect_inconsistencies([devis, facture])
    amount_alerts = [a for a in alerts if a.alert_type == AlertType.AMOUNT_INCONSISTENCY]
    assert len(amount_alerts) == 0  # 4% < 5% de tolérance


def test_alert_when_amounts_exceed_tolerance():
    devis = make_silver(DocumentType.DEVIS, montant_ttc=Decimal("1000.00"), emetteur_nom="Acme")
    facture = make_silver(DocumentType.FACTURE, montant_ttc=Decimal("1200.00"), emetteur_nom="Acme")
    alerts = detect_inconsistencies([devis, facture])
    amount_alerts = [a for a in alerts if a.alert_type == AlertType.AMOUNT_INCONSISTENCY]
    assert len(amount_alerts) == 1
    assert amount_alerts[0].severity == AlertSeverity.HAUTE


def test_no_alert_when_different_emetteurs():
    devis = make_silver(DocumentType.DEVIS, montant_ttc=Decimal("1000.00"), emetteur_nom="Acme")
    facture = make_silver(
        DocumentType.FACTURE,
        montant_ttc=Decimal("5000.00"),
        emetteur_nom="AutreEntreprise",
    )
    alerts = detect_inconsistencies([devis, facture])
    amount_alerts = [a for a in alerts if a.alert_type == AlertType.AMOUNT_INCONSISTENCY]
    assert len(amount_alerts) == 0


# ─── Règle 4 : Incohérence dates ─────────────────────────────────────────────

def test_alert_when_facture_before_devis():
    devis = make_silver(DocumentType.DEVIS, date_emission="2024-06-01", emetteur_nom="Acme")
    facture = make_silver(DocumentType.FACTURE, date_emission="2024-05-01", emetteur_nom="Acme")
    alerts = detect_inconsistencies([devis, facture])
    date_alerts = [a for a in alerts if a.alert_type == AlertType.DATE_INCOHERENCE]
    assert len(date_alerts) == 1
    assert date_alerts[0].severity == AlertSeverity.MOYENNE


def test_no_alert_when_facture_after_devis():
    devis = make_silver(DocumentType.DEVIS, date_emission="2024-04-01", emetteur_nom="Acme")
    facture = make_silver(DocumentType.FACTURE, date_emission="2024-05-01", emetteur_nom="Acme")
    alerts = detect_inconsistencies([devis, facture])
    date_alerts = [a for a in alerts if a.alert_type == AlertType.DATE_INCOHERENCE]
    assert len(date_alerts) == 0


# ─── Cas multi-alertes ───────────────────────────────────────────────────────

def test_multiple_alerts_detected_simultaneously():
    devis = make_silver(
        DocumentType.DEVIS,
        siret="12345678901234",
        emetteur_nom="Acme SARL",
        montant_ttc=Decimal("1000.00"),
        date_emission="2024-06-01",
    )
    facture = make_silver(
        DocumentType.FACTURE,
        siret="98765432109876",  # SIRET différent → alerte
        emetteur_nom="Acme SARL",
        montant_ttc=Decimal("2000.00"),  # Montant différent → alerte
        date_emission="2024-05-01",  # Date avant devis → alerte
    )
    alerts = detect_inconsistencies([devis, facture])
    assert len(alerts) >= 3
