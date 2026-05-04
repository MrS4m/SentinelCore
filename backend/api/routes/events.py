"""
SentinelCore - Rota de Eventos
Recebe dados dos agentes, processa e gera alertas via IA
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from db.database import get_db
from db.models import Agent, Event, Alert, Client, SeverityLevel, AlertStatus
from core.ai.engine import AIEngine
from workers.alert_processor import process_alert_async
from api.middleware.auth import get_current_client

logger = logging.getLogger("sentinelcore.routes.events")
router = APIRouter()


# ------------------------------------------------------------------ #
#  SCHEMAS                                                             #
# ------------------------------------------------------------------ #

class EventPayload(BaseModel):
    agent_id:  str
    timestamp: str
    hostname:  str
    os:        str
    data:      dict


class EventResponse(BaseModel):
    status:           str
    events_received:  int
    alerts_generated: int
    actions:          list = []


# ------------------------------------------------------------------ #
#  ENDPOINT PRINCIPAL                                                  #
# ------------------------------------------------------------------ #

@router.post("", response_model=EventResponse)
async def receive_event(
    payload:          EventPayload,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
    client:           Client = Depends(get_current_client),
):
    """
    Endpoint principal — recebe dados do agente, persiste e dispara análise.
    Retorna ações a serem executadas pelo agente.
    """

    # 1. Atualiza last_seen do agente
    agent = await _get_or_create_agent(db, payload, client)

    # 2. Persiste o evento bruto
    event = Event(
        agent_id=agent.id,
        client_id=client.id,
        event_type="full_collection",
        raw_data=payload.dict(),
        received_at=datetime.utcnow(),
    )
    db.add(event)
    await db.flush()

    # 3. Análise rápida de severidade (síncrona, sem IA — para decidir se precisa de alerta)
    quick_severity = _quick_severity_check(payload.data)

    alerts_generated = 0
    pending_actions = []

    # 4. Se há dados relevantes, dispara análise com IA em background
    if quick_severity != "INFO":
        background_tasks.add_task(
            process_alert_async,
            event_id=event.id,
            event_data=payload.dict(),
            client_id=client.id,
            agent_id=agent.id,
            quick_severity=quick_severity,
        )
        alerts_generated = 1  # estimativa — o real será processado em background

    # 5. Verifica se há ações pendentes para este agente
    pending_actions = await _get_pending_actions(db, agent.id)

    await db.commit()

    logger.info(
        f"Evento recebido | Cliente: {client.name} | "
        f"Host: {payload.hostname} | Severidade: {quick_severity}"
    )

    return EventResponse(
        status="ok",
        events_received=1,
        alerts_generated=alerts_generated,
        actions=pending_actions,
    )


# ------------------------------------------------------------------ #
#  ANÁLISE RÁPIDA (sem IA — regras simples para triagem)               #
# ------------------------------------------------------------------ #

def _quick_severity_check(data: dict) -> str:
    """
    Analisa dados rapidamente sem IA para decidir a prioridade.
    Retorna INFO se não há nada relevante (economiza tokens de IA).
    """
    # CVEs críticos
    cve_data = data.get("cve", {})
    if cve_data.get("critical_count", 0) >= 1:
        return "CRITICAL"
    if cve_data.get("high_count", 0) >= 3:
        return "HIGH"

    # Processos suspeitos
    procs = data.get("processes", {})
    if procs.get("suspicious"):
        worst = max(
            (p.get("severity", "LOW") for p in procs["suspicious"]),
            key=lambda s: {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(s, 0),
            default="LOW"
        )
        if worst in ("CRITICAL", "HIGH"):
            return worst

    # Logs com ameaças
    logs = data.get("logs", [])
    alert_logs = [l for l in logs if l.get("has_alert")]
    critical_logs = [l for l in alert_logs if l.get("severity") in ("CRITICAL", "HIGH")]
    if critical_logs:
        return "HIGH"

    # IPs maliciosos confirmados
    net = data.get("network", {})
    malicious = [ip for ip in net.get("ip_reputation", []) if ip.get("is_malicious")]
    if malicious:
        return "HIGH"

    # Conexões suspeitas
    if net.get("suspicious_outbound"):
        return "MEDIUM"

    # Portas de alto risco
    ports = data.get("ports", {})
    if ports.get("high_risk"):
        return "MEDIUM"

    if alert_logs:
        return "LOW"

    return "INFO"


# ------------------------------------------------------------------ #
#  HELPERS                                                             #
# ------------------------------------------------------------------ #

async def _get_or_create_agent(db: AsyncSession, payload: EventPayload, client: Client) -> Agent:
    """Busca agente existente ou cria novo."""
    result = await db.execute(
        select(Agent).where(Agent.agent_id == payload.agent_id)
    )
    agent = result.scalar_one_or_none()

    if agent:
        # Atualiza last_seen e hostname (pode ter mudado)
        agent.last_seen = datetime.utcnow()
        agent.hostname = payload.hostname
        agent.is_online = True
    else:
        agent = Agent(
            client_id=client.id,
            agent_id=payload.agent_id,
            hostname=payload.hostname,
            os=payload.os,
            last_seen=datetime.utcnow(),
            first_seen=datetime.utcnow(),
        )
        db.add(agent)
        await db.flush()
        logger.info(f"Novo agente registrado: {payload.hostname} ({payload.agent_id})")

    return agent


async def _get_pending_actions(db: AsyncSession, agent_id: str) -> list:
    """Busca ações pendentes para o agente e as marca como enviadas."""
    from db.models import RemoteAction, ActionStatus

    result = await db.execute(
        select(RemoteAction).where(
            RemoteAction.agent_id == agent_id,
            RemoteAction.status == ActionStatus.PENDING,
        )
    )
    actions = result.scalars().all()

    pending = []
    for action in actions:
        pending.append({
            "id":     action.id,
            "type":   action.action_type,
            "params": action.params,
        })
        action.status = ActionStatus.SENT

    return pending
