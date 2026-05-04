"""
SentinelCore - Rate Limiting
Limita requisições por IP para evitar abuso
"""

import time
import logging
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse

from config.settings import get_settings

logger = logging.getLogger("sentinelcore.ratelimit")
settings = get_settings()

# Armazenamento em memória (em produção usar Redis)
_request_counts: dict = defaultdict(list)


class RateLimitMiddleware:
    async def __call__(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60  # janela de 1 minuto

        # Limpa entradas antigas
        _request_counts[client_ip] = [
            t for t in _request_counts[client_ip]
            if now - t < window
        ]

        if len(_request_counts[client_ip]) >= settings.rate_limit_per_minute:
            logger.warning(f"Rate limit atingido: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Muitas requisições. Tente novamente em 1 minuto."},
            )

        _request_counts[client_ip].append(now)
        return await call_next(request)
