"""Service de détection d'incohérences et fraudes inter-documents."""
import logging
import re
import uuid
from decimal import Decimal

from app.schemas.datalake import SilverRecord
from app.schemas.document import DocumentType
from app.schemas.fraud import AlertSeverity, AlertType, InconsistencyAlert

logger = logging.getLogger(__name__)

# Tolérance pour la comparaison de montants (5%)
AMOUNT_TOLERANCE_RATIO = Decimal("0.05")


def detect_inconsistencies(records: list[SilverRecord]) -> list[InconsistencyAlert]:
    """
    Analyse un ensemble de SilverRecords et retourne toutes les alertes détectées.
    Les règles s'appliquent sur l'ensemble du batch de documents.
    """
    alerts: list[InconsistencyAlert] = []

    alerts.extend(_check_siren_format(records))
    alerts.extend(_check_siret_mismatch(records))
    alerts.extend(_check_amount_inconsistency(records))
    alerts.extend(_check_date_incoherence(records))

    logger.info("%d alertes détectées sur %d documents", len(alerts), len(records))
    return alerts


# ─── Règle 1 : Format SIREN invalide ─────────────────────────────────────────

def _check_siren_format(records: list[SilverRecord]) -> list[InconsistencyAlert]:
    alerts = []
    for rec in records:
        ext = rec.extraction
        if ext.siren is not None and not re.fullmatch(r"\d{9}", ext.siren):
            alerts.append(InconsistencyAlert(
                id=str(uuid.uuid4()),
                alert_type=AlertType.SIREN_FORMAT_INVALID,
                severity=AlertSeverity.HAUTE,
                description=f"SIREN '{ext.siren}' invalide dans '{rec.original_filename}'",
                document_ids=[rec.document_id],
                field_in_conflict="siren",
                value_a=ext.siren,
                suggestion="Vérifier le numéro SIREN du document source.",
            ))
    return alerts


# ─── Règle 2 : SIRET incohérent entre documents ───────────────────────────────

def _check_siret_mismatch(records: list[SilverRecord]) -> list[InconsistencyAlert]:
    """Détecte si deux documents avec le même émetteur ont des SIRET différents."""
    alerts = []
    # Grouper par nom d'émetteur (normalisé)
    by_emetteur: dict[str, list[SilverRecord]] = {}
    for rec in records:
        nom = (rec.extraction.emetteur_nom or "").strip().lower()
        if nom:
            by_emetteur.setdefault(nom, []).append(rec)

    for emetteur, group in by_emetteur.items():
        sirets = {
            rec.document_id: rec.extraction.siret
            for rec in group
            if rec.extraction.siret
        }
        unique_sirets = set(sirets.values())
        if len(unique_sirets) > 1:
            doc_ids = list(sirets.keys())
            siret_vals = list(unique_sirets)
            alerts.append(InconsistencyAlert(
                id=str(uuid.uuid4()),
                alert_type=AlertType.SIRET_MISMATCH,
                severity=AlertSeverity.CRITIQUE,
                description=(
                    f"SIRET incohérent pour l'émetteur '{emetteur}' : "
                    f"{siret_vals[0]} vs {siret_vals[1]}"
                ),
                document_ids=doc_ids,
                field_in_conflict="siret",
                value_a=siret_vals[0],
                value_b=siret_vals[1],
                suggestion="Vérifier l'identité légale de l'émetteur auprès du registre SIRENE.",
            ))
    return alerts


# ─── Règle 3 : Incohérence montant devis vs facture ──────────────────────────

def _check_amount_inconsistency(records: list[SilverRecord]) -> list[InconsistencyAlert]:
    """Compare les montants TTC entre devis et factures du même émetteur."""
    alerts = []
    devis = [r for r in records if r.document_type == DocumentType.DEVIS]
    factures = [r for r in records if r.document_type == DocumentType.FACTURE]

    for d in devis:
        if not d.extraction.montants.ttc:
            continue
        emetteur_d = (d.extraction.emetteur_nom or "").strip().lower()

        for f in factures:
            if not f.extraction.montants.ttc:
                continue
            emetteur_f = (f.extraction.emetteur_nom or "").strip().lower()

            if emetteur_d and emetteur_d == emetteur_f:
                ttc_devis = d.extraction.montants.ttc
                ttc_facture = f.extraction.montants.ttc
                diff = abs(ttc_devis - ttc_facture)
                tolerance = ttc_devis * AMOUNT_TOLERANCE_RATIO

                if diff > tolerance:
                    alerts.append(InconsistencyAlert(
                        id=str(uuid.uuid4()),
                        alert_type=AlertType.AMOUNT_INCONSISTENCY,
                        severity=AlertSeverity.HAUTE,
                        description=(
                            f"Montant TTC du devis ({ttc_devis} €) diffère de "
                            f"la facture ({ttc_facture} €) pour '{emetteur_d}' "
                            f"(écart de {diff:.2f} €)"
                        ),
                        document_ids=[d.document_id, f.document_id],
                        field_in_conflict="montants.ttc",
                        value_a=str(ttc_devis),
                        value_b=str(ttc_facture),
                        suggestion=(
                            "Vérifier si un avenant ou modification de commande"
                            " justifie cet écart."
                        ),
                    ))
    return alerts


# ─── Règle 4 : Incohérence de dates ──────────────────────────────────────────

def _check_date_incoherence(records: list[SilverRecord]) -> list[InconsistencyAlert]:
    """Détecte une facture avec une date antérieure au devis du même émetteur."""
    alerts = []
    devis = [
        r for r in records
        if r.document_type == DocumentType.DEVIS and r.extraction.date_emission
    ]
    factures = [
        r for r in records
        if r.document_type == DocumentType.FACTURE and r.extraction.date_emission
    ]

    for d in devis:
        emetteur_d = (d.extraction.emetteur_nom or "").strip().lower()
        date_devis = d.extraction.date_emission

        for f in factures:
            emetteur_f = (f.extraction.emetteur_nom or "").strip().lower()
            date_facture = f.extraction.date_emission

            if emetteur_d and emetteur_d == emetteur_f:
                if date_facture and date_devis and date_facture < date_devis:
                    alerts.append(InconsistencyAlert(
                        id=str(uuid.uuid4()),
                        alert_type=AlertType.DATE_INCOHERENCE,
                        severity=AlertSeverity.MOYENNE,
                        description=(
                            f"La facture ('{date_facture}') est antérieure"
                            f" au devis ('{date_devis}')"
                            f" pour l'émetteur '{emetteur_d}'"
                        ),
                        document_ids=[d.document_id, f.document_id],
                        field_in_conflict="date_emission",
                        value_a=date_devis,
                        value_b=date_facture,
                        suggestion="Une facture ne peut pas précéder le devis correspondant.",
                    ))
    return alerts
