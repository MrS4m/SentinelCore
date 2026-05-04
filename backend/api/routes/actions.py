"""
SentinelCore - Rota: Actions
Disparo manual de ações remotas nos agentes
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from db.database import get_db
from db.models import Agent, RemoteAction, ActionStatus, Client
from api.middleware.auth import get_current_client

logger = logging.getLogger("sentinelcore.routes.actions")
router = APIRouter()

ALLOWED_ACTIONS = {
    "block_ip", "unblock_ip", "ban_ip_fail2ban",
    "kill_process", "disable_user", "enable_user",
    "restart_service", "isolate_host", "collect_forensics",
}


class ActionRequest(BaseModel):
    agent_hostname: str
    action_type:    str
    params:         dict = {}
    reason:         str  = ""


@router.post("")
async def dispatch_action(
    payload: ActionRequest,
    db:      AsyncSession  = Depends(get_db),
    client:  Client        = Depends(get_current_client),
):
    """Cria uma ação remota que será enviada ao agente no próximo ciclo."""
    if payload.action_type not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Ação '{payload.action_type}' não permitida")

    # Busca agente pelo hostname
    result = await db.execute(
        select(Agent).where(
            Agent.hostname == payload.agent_hostname,
            Agent.client_id == client.id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    action = RemoteAction(
        agent_id     = agent.id,
        action_type  = payload.action_type,
        params       = payload.params,
        status       = ActionStatus.PENDING,
        triggered_by = "manual",
        created_at   = datetime.utcnow(),
    )
    db.add(action)
    await db.commit()

    logger.info(
        f"Ação manual criada: {payload.action_type} | "
        f"Host: {payload.agent_hostname} | Razão: {payload.reason}"
    )
    return {"action_id": action.id, "status": "pending", "message": "Ação será executada no próximo ciclo do agente"}


@router.post("/{action_id}/result")
async def receive_action_result(
    action_id: str,
    result:    dict,
    db:        AsyncSession = Depends(get_db),
):
    """Recebe o resultado de uma ação executada pelo agente."""
    q = await db.execute(select(RemoteAction).where(RemoteAction.id == action_id))
    action = q.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Ação não encontrada")

    action.status      = ActionStatus.EXECUTED if result.get("success") else ActionStatus.FAILED
    action.result      = result
    action.executed_at = datetime.utcnow()
    await db.commit()

    logger.info(f"Resultado de ação {action_id}: {'✅ sucesso' if result.get('success') else '❌ falhou'}")
    return {"status": "recorded"}
