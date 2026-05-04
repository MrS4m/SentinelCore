"""
SentinelCore - Rotas: Agents
"""
import secrets
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from db.database import get_db
from db.models import Agent, Client
from api.middleware.auth import get_current_client

logger = logging.getLogger("sentinelcore.routes.agents")
router = APIRouter()


class AgentRegisterPayload(BaseModel):
    agent_id:   str
    hostname:   str
    os:         str
    os_version: str | None = None
    arch:       str | None = None
    token:      str
    version:    str = "1.0.0"


@router.post("/register")
async def register_agent(
    payload: AgentRegisterPayload,
    db: AsyncSession = Depends(get_db),
):
    """Registra ou atualiza um agente."""
    # Valida token do cliente
    result = await db.execute(
        select(Client).where(Client.api_token == payload.token, Client.is_active == True)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Upsert do agente
    result = await db.execute(select(Agent).where(Agent.agent_id == payload.agent_id))
    agent = result.scalar_one_or_none()

    if agent:
        agent.hostname   = payload.hostname
        agent.os         = payload.os
        agent.os_version = payload.os_version
        agent.last_seen  = datetime.utcnow()
        agent.is_online  = True
        agent.version    = payload.version
    else:
        agent = Agent(
            client_id  = client.id,
            agent_id   = payload.agent_id,
            hostname   = payload.hostname,
            os         = payload.os,
            os_version = payload.os_version,
            arch       = payload.arch,
            version    = payload.version,
            last_seen  = datetime.utcnow(),
        )
        db.add(agent)

    await db.commit()
    return {"status": "registered", "client_name": client.name}


@router.get("")
async def list_agents(
    db:     AsyncSession = Depends(get_db),
    client: Client       = Depends(get_current_client),
):
    """Lista todos os agentes do cliente."""
    result = await db.execute(select(Agent).where(Agent.client_id == client.id))
    agents = result.scalars().all()
    return [
        {
            "id":         a.id,
            "hostname":   a.hostname,
            "os":         a.os,
            "is_online":  a.is_online,
            "last_seen":  a.last_seen,
            "risk_score": a.risk_score,
            "version":    a.version,
        }
        for a in agents
    ]
