"""Routes API pour le CRM fournisseurs et le dashboard conformité."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import require_admin, require_auth
from app.schemas.business import (
    SupplierSummary,
    build_supplier_key,
    group_type_of,
)
from app.schemas.datalake import GoldRecord
from app.schemas.fraud import AlertSeverity
from app.storage import datalake
from app.db.mongodb import get_collection


def _get_user_doc_ids(owner_id: str) -> set[str]:
    """Retourne les IDs des documents appartenant à l'utilisateur."""
    try:
        cursor = get_collection("bronze").find(
            {"document.owner_id": owner_id},
            {"document.id": 1}
        )
        return {doc["document"]["id"] for doc in cursor}
    except Exception:
        return set()


router = APIRouter(tags=["business"])


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _match_gold_to_key(gold: GoldRecord, supplier_key: str) -> bool:
    return build_supplier_key(gold.extraction.siren, gold.extraction.emetteur_nom) == supplier_key


def _build_supplier_summaries(gold_records: list[GoldRecord]) -> list[SupplierSummary]:
    """Construit la liste des fournisseurs groupés par clé composite."""
    suppliers: dict[str, dict] = {}
    for gold in gold_records:
        ext = gold.extraction
        key = build_supplier_key(ext.siren, ext.emetteur_nom)
        nom = (ext.emetteur_nom or "").strip() or "Émetteur inconnu"
        if key not in suppliers:
            suppliers[key] = {
                "supplier_key": key,
                "group_type": group_type_of(key),
                "siren": ext.siren,
                "nom": nom,
                "nombre_documents": 0,
                "total_ttc": 0.0,
                "a_des_alertes": False,
                "types_documents": set(),
            }
        else:
            if suppliers[key]["nom"] == "Émetteur inconnu" and nom != "Émetteur inconnu":
                suppliers[key]["nom"] = nom
        s = suppliers[key]
        s["nombre_documents"] += 1
        if ext.montants.ttc:
            s["total_ttc"] += float(ext.montants.ttc)
        if gold.alerts:
            s["a_des_alertes"] = True
        s["types_documents"].add(gold.document_type.value)

    order = {"siren": 0, "nom": 1, "inconnu": 2}
    sorted_suppliers = sorted(suppliers.values(), key=lambda v: (order[v["group_type"]], v["nom"]))
    return [
        SupplierSummary(
            supplier_key=v["supplier_key"],
            group_type=v["group_type"],
            siren=v["siren"],
            nom=v["nom"],
            nombre_documents=v["nombre_documents"],
            total_ttc=round(v["total_ttc"], 2),
            a_des_alertes=v["a_des_alertes"],
            types_documents=list(v["types_documents"]),
        )
        for v in sorted_suppliers
    ]


# ─── CRM ─────────────────────────────────────────────────────────────────────


@router.get("/api/crm/suppliers", response_model=list[SupplierSummary])
async def get_crm_suppliers(_: dict = Depends(require_admin)) -> list[SupplierSummary]:
    """Données CRM admin : tous les fournisseurs groupés par clé composite."""
    return _build_supplier_summaries(datalake.load_all_gold())


@router.get("/api/crm/my-suppliers", response_model=list[SupplierSummary])
async def get_my_crm_suppliers(payload: dict = Depends(require_auth)) -> list[SupplierSummary]:
    """Données CRM utilisateur : fournisseurs de ses propres documents."""
    owner_id = payload["sub"]
    doc_ids = _get_user_doc_ids(owner_id)
    gold_records = [g for g in datalake.load_all_gold() if str(g.document_id) in doc_ids]
    return _build_supplier_summaries(gold_records)


@router.get("/api/crm/suppliers/{supplier_key:path}", response_model=list[GoldRecord])
async def get_supplier_documents(
    supplier_key: str,
    _: dict = Depends(require_admin),
) -> list[GoldRecord]:
    """Historique de tous les documents Gold d'une supplier_key composite (admin)."""
    if not supplier_key:
        raise HTTPException(status_code=400, detail="supplier_key invalide")
    gold_records = datalake.load_all_gold()
    matched = [g for g in gold_records if _match_gold_to_key(g, supplier_key)]
    matched.sort(key=lambda g: g.curated_at, reverse=True)
    return matched


@router.get("/api/crm/my-suppliers/{supplier_key:path}", response_model=list[GoldRecord])
async def get_my_supplier_documents(
    supplier_key: str,
    payload: dict = Depends(require_auth),
) -> list[GoldRecord]:
    """Documents Gold d'une supplier_key pour l'utilisateur connecté."""
    if not supplier_key:
        raise HTTPException(status_code=400, detail="supplier_key invalide")
    owner_id = payload["sub"]
    doc_ids = _get_user_doc_ids(owner_id)
    gold_records = datalake.load_all_gold()
    matched = [g for g in gold_records if _match_gold_to_key(g, supplier_key) and str(g.document_id) in doc_ids]
    matched.sort(key=lambda g: g.curated_at, reverse=True)
    return matched


# ─── Conformité ───────────────────────────────────────────────────────────────


class ComplianceDashboardSchema(BaseModel):
    total_documents: int
    documents_conformes: int
    documents_non_conformes: int
    taux_conformite: float
    alertes_critiques: int
    alertes_hautes: int
    alertes_moyennes: int
    alertes_totales: int


def _build_compliance_dashboard(gold_records: list[GoldRecord]) -> ComplianceDashboardSchema:
    total = len(gold_records)
    conformes = sum(1 for g in gold_records if g.is_compliant)
    seen_ids: set[str] = set()
    critiques = hautes = moyennes = 0
    for gold in gold_records:
        for alert in gold.alerts:
            if alert.id not in seen_ids:
                seen_ids.add(alert.id)
                if alert.severity == AlertSeverity.CRITIQUE:
                    critiques += 1
                elif alert.severity == AlertSeverity.HAUTE:
                    hautes += 1
                elif alert.severity == AlertSeverity.MOYENNE:
                    moyennes += 1
    return ComplianceDashboardSchema(
        total_documents=total,
        documents_conformes=conformes,
        documents_non_conformes=total - conformes,
        taux_conformite=round(conformes / total * 100, 1) if total > 0 else 100.0,
        alertes_critiques=critiques,
        alertes_hautes=hautes,
        alertes_moyennes=moyennes,
        alertes_totales=len(seen_ids),
    )


@router.get("/api/compliance/dashboard", response_model=ComplianceDashboardSchema)
async def get_compliance_dashboard(_: dict = Depends(require_admin)) -> ComplianceDashboardSchema:
    """Dashboard conformité admin : métriques globales."""
    return _build_compliance_dashboard(datalake.load_all_gold())


@router.get("/api/compliance/my-dashboard", response_model=ComplianceDashboardSchema)
async def get_my_compliance_dashboard(payload: dict = Depends(require_auth)) -> ComplianceDashboardSchema:
    """Dashboard conformité utilisateur : métriques de ses propres documents."""
    owner_id = payload["sub"]
    doc_ids = _get_user_doc_ids(owner_id)
    gold_records = [g for g in datalake.load_all_gold() if str(g.document_id) in doc_ids]
    return _build_compliance_dashboard(gold_records)
