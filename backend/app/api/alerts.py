"""Routes API pour les alertes de fraude (zone Gold)."""

from fastapi import APIRouter, Depends

from app.api.auth import require_admin, require_auth
from app.schemas.fraud import AlertSeverity, AlertType, InconsistencyAlert
from app.storage import datalake
from app.db.mongodb import get_collection


def _get_user_doc_ids(owner_id: str) -> set[str]:
    try:
        cursor = get_collection("bronze").find(
            {"document.owner_id": owner_id},
            {"document.id": 1}
        )
        return {doc["document"]["id"] for doc in cursor}
    except Exception:
        return set()


def _extract_alerts(gold_records, severity=None, alert_type=None) -> list[InconsistencyAlert]:
    severity_order = {
        AlertSeverity.CRITIQUE: 0,
        AlertSeverity.HAUTE: 1,
        AlertSeverity.MOYENNE: 2,
        AlertSeverity.FAIBLE: 3,
    }
    seen_ids: set[str] = set()
    all_alerts: list[InconsistencyAlert] = []
    for gold in gold_records:
        for alert in gold.alerts:
            if alert.id not in seen_ids:
                seen_ids.add(alert.id)
                all_alerts.append(alert)
    if severity:
        all_alerts = [a for a in all_alerts if a.severity == severity]
    if alert_type:
        all_alerts = [a for a in all_alerts if a.alert_type == alert_type]
    all_alerts.sort(key=lambda a: severity_order.get(a.severity, 99))
    return all_alerts

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/", response_model=list[InconsistencyAlert])
async def list_alerts(
    severity: AlertSeverity | None = None,
    alert_type: AlertType | None = None,
    _: dict = Depends(require_admin),
) -> list[InconsistencyAlert]:
    """Liste toutes les alertes (admin)."""
    return _extract_alerts(datalake.load_all_gold(), severity, alert_type)


@router.get("/my", response_model=list[InconsistencyAlert])
async def list_my_alerts(
    severity: AlertSeverity | None = None,
    alert_type: AlertType | None = None,
    payload: dict = Depends(require_auth),
) -> list[InconsistencyAlert]:
    """Liste les alertes des documents de l'utilisateur connecté."""
    owner_id = payload["sub"]
    doc_ids = _get_user_doc_ids(owner_id)
    gold_records = [g for g in datalake.load_all_gold() if str(g.document_id) in doc_ids]
    return _extract_alerts(gold_records, severity, alert_type)
