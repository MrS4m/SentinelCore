"""
SentinelCore - Fila de Workers
Inicialização simples com asyncio (sem Celery para manter leveza)
"""
import logging

logger = logging.getLogger("sentinelcore.queue")


async def init_queue():
    """Inicializa a fila de processamento background."""
    logger.info("Fila de processamento assíncrono pronta (asyncio nativo)")
