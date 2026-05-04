"""
SentinelCore - Rotas: Alerts
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel

from db.database import get_db
from db.models import Alert, AlertStatus, SeverityLevel, Client
from api.middleware.auth import get_current_client
from core.ai.engine import AIEngine

logger = logging.getLogger("sentinelcore.routes.alerts")
router = APIRouter()


@router.get("")
async def list_alerts(
    severity: str | None   = Query(None),
    status:   str | None   = Query(None),
    limit:    int           = Query(50, le=200),
    offset:   int           = Query(0),
    db:       AsyncSession  = Depends(get_db),
    client:   Client        = Depends(get_current_client),
):
    """Lista alertas do cliente com filtros."""
    q = select(Alert).where(Alert.client_id == client.id)

    if severity:
        q = q.where(Alert.severity == SeverityLevel(severity.upper()))
    if status:
        q = q.where(Alert.status == AlertStatus(status.upper()))

    q = q.order_by(desc(Alert.created_at)).limit(limit).offset(offset)
    result = await db.execute(q)
    alerts = result.scalars().all()

    return [_alert_to_dict(a) for a in alerts]


@router.get("/{alert_id}")
async def get_alert(
    alert_id: str,
    db:       AsyncSession = Depends(get_db),
    client:   Client       = Depends(get_current_client),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.client_id == client.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    return _alert_to_dict(alert)


@router.patch("/{alert_id}/ack")
async def ack_alert(
    alert_id: str,
    db:       AsyncSession = Depends(get_db),
    client:   Client       = Depends(get_current_client),
):
    """Reconhece um alerta (ACK)."""
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.client_id == client.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")

    alert.status   = AlertStatus.ACK
    alert.acked_by = client.name
    await db.commit()
    return {"status": "acked"}


@router.patch("/{alert_id}/resolve")
async def resolve_alert(
    alert_id:   str,
    resolution: dict,
    db:         AsyncSession = Depends(get_db),
    client:     Client       = Depends(get_current_client),
):
    """Marca alerta como resolvido e aprende com a resolução (RAG)."""
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.client_id == client.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")

    alert.status      = AlertStatus.RESOLVED
    alert.resolved_at = datetime.utcnow()
    await db.commit()

    # Envia para o RAG aprender com a resolução
    if AIEngine._rag_engine:
        await AIEngine._rag_engine.add_resolved_incident(
            _alert_to_dict(alert),
            resolution.get("description", "Resolvido pelo operador"),
        )

    return {"status": "resolved"}


def _alert_to_dict(a: Alert) -> dict:
    return {
        "id":              a.id,
        "title":           a.title,
        "severity":        a.severity.value if hasattr(a.severity, "value") else a.severity,
        "category":        a.category,
        "status":          a.status.value if hasattr(a.status, "value") else a.status,
        "description":     a.description,
        "ai_analysis":     a.ai_analysis,
        "remediation":     a.remediation,
        "risk_score":      a.risk_score,
        "source_ip":       a.source_ip,
        "affected_asset":  a.affected_asset,
        "cve_ids":         a.cve_ids,
        "auto_remediated": a.auto_remediated,
        "notified":        a.notified,
        "ai_model_used":   a.ai_model_used,
        "created_at":      a.created_at.isoformat() if a.created_at else None,
        "resolved_at":     a.resolved_at.isoformat() if a.resolved_at else None,
    }
