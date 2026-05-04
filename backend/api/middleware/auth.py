"""
SentinelCore - Middleware de Autenticação
Valida tokens de agentes e de usuários da API
"""

import logging
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import Client

logger = logging.getLogger("sentinelcore.auth")
security = HTTPBearer()


class AuthMiddleware:
    """Middleware que injeta client_id em todas as requisições autenticadas."""

    async def __call__(self, request: Request, call_next):
        # Rotas públicas (sem autenticação)
        public_paths = {"/health", "/api/docs", "/api/redoc", "/api/openapi.json"}
        if request.url.path in public_paths:
            return await call_next(request)

        return await call_next(request)


async def get_current_client(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Client:
    """
    Dependency que valida o Bearer token e retorna o cliente.
    Usado em todas as rotas que requerem autenticação.
    """
    token = credentials.credentials

    result = await db.execute(
        select(Client).where(
            Client.api_token == token,
            Client.is_active == True,
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        logger.warning(f"Token inválido: {token[:8]}...")
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    return client
