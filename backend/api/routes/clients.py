"""
SentinelCore - Rotas: Clients
"""
import secrets
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from db.database import get_db
from db.models import Client

logger = logging.getLogger("sentinelcore.routes.clients")
router = APIRouter()


class ClientCreate(BaseModel):
    name:  str
    email: str
    phone: str | None = None
    plan:  str = "basic"


@router.post("")
async def create_client(
    payload: ClientCreate,
    db:      AsyncSession = Depends(get_db),
):
    """Cria um novo cliente e gera token de API."""
    # Verifica email duplicado
    existing = await db.execute(select(Client).where(Client.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    token = secrets.token_hex(32)
    client = Client(
        name      = payload.name,
        email     = payload.email,
        phone     = payload.phone,
        plan      = payload.plan,
        api_token = token,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)

    logger.info(f"Cliente criado: {client.name} ({client.id})")
    return {
        "id":        client.id,
        "name":      client.name,
        "email":     client.email,
        "api_token": token,  # retorna apenas na criação
        "plan":      client.plan,
    }


@router.get("")
async def list_clients(db: AsyncSession = Depends(get_db)):
    """Lista todos os clientes (rota admin)."""
    result = await db.execute(select(Client).where(Client.is_active == True))
    clients = result.scalars().all()
    return [
        {"id": c.id, "name": c.name, "email": c.email, "plan": c.plan}
        for c in clients
    ]
