"""
SentinelCore - Rota: Dashboard
Resumo executivo para o painel do cliente
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta

from db.database import get_db
from db.models import Alert, Agent, SeverityLevel, AlertStatus, Client
from api.middleware.auth import get_current_client

logger = logging.getLogger("sentinelcore.routes.dashboard")
router = APIRouter()


@router.get("/summary")
async def get_summary(
    db:     AsyncSession = Depends(get_db),
    client: Client       = Depends(get_current_client),
):
    """Resumo executivo: contagens, risk score, alertas recentes."""
    since_24h = datetime.utcnow() - timedelta(hours=24)
    since_7d  = datetime.utcnow() - timedelta(days=7)

    # Contagem de agentes
    agents_result = await db.execute(
        select(func.count()).where(Agent.client_id == client.id)
    )
    total_agents = agents_result.scalar() or 0

    online_result = await db.execute(
        select(func.count()).where(Agent.client_id == client.id, Agent.is_online == True)
    )
    online_agents = online_result.scalar() or 0

    # Alertas por severidade (últimas 24h)
    alerts_result = await db.execute(
        select(Alert.severity, func.count())
        .where(Alert.client_id == client.id, Alert.created_at >= since_24h)
        .group_by(Alert.severity)
    )
    alerts_by_severity = {str(row[0].value if hasattr(row[0], "value") else row[0]): row[1]
                          for row in alerts_result.all()}

    # Alertas abertos
    open_result = await db.execute(
        select(func.count()).where(
            Alert.client_id == client.id,
            Alert.status == AlertStatus.OPEN,
        )
    )
    open_alerts = open_result.scalar() or 0

    # Risk score médio dos agentes
    risk_result = await db.execute(
        select(func.avg(Agent.risk_score)).where(Agent.client_id == client.id)
    )
    avg_risk = round(float(risk_result.scalar() or 0), 1)

    # 5 alertas mais recentes
    recent_result = await db.execute(
        select(Alert)
        .where(Alert.client_id == client.id)
        .order_by(desc(Alert.created_at))
        .limit(5)
    )
    recent_alerts = [
        {
            "id":             a.id,
            "title":          a.title,
            "severity":       a.severity.value if hasattr(a.severity, "value") else a.severity,
            "category":       a.category,
            "affected_asset": a.affected_asset,
            "created_at":     a.created_at.isoformat() if a.created_at else None,
        }
        for a in recent_result.scalars().all()
    ]

    return {
        "agents": {
            "total":  total_agents,
            "online": online_agents,
            "offline": total_agents - online_agents,
        },
        "alerts_24h": {
            "critical": alerts_by_severity.get("CRITICAL", 0),
            "high":     alerts_by_severity.get("HIGH", 0),
            "medium":   alerts_by_severity.get("MEDIUM", 0),
            "low":      alerts_by_severity.get("LOW", 0),
            "open":     open_alerts,
        },
        "risk_score":    avg_risk,
        "recent_alerts": recent_alerts,
        "generated_at":  datetime.utcnow().isoformat(),
    }
