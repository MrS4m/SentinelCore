"""
SentinelCore Backend - Main Application
"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import agents, events, alerts, clients, dashboard, actions
from core.ai.engine import AIEngine
from db.database import init_db
from workers.queue import init_queue
from config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sentinelcore.app")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SentinelCore Backend iniciando...")
    await init_db()
    logger.info("Banco de dados conectado")
    await init_queue()
    logger.info("Fila de workers iniciada")
    await AIEngine.initialize()
    logger.info("Motor de IA pronto")
    logger.info("SentinelCore Backend online!")
    yield
    logger.info("Encerrando SentinelCore Backend...")


app = FastAPI(
    title="SentinelCore API",
    description="Plataforma de analise de vulnerabilidades e seguranca para PMEs",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router,    prefix="/api/v1/agents",    tags=["Agents"])
app.include_router(events.router,    prefix="/api/v1/events",    tags=["Events"])
app.include_router(alerts.router,    prefix="/api/v1/alerts",    tags=["Alerts"])
app.include_router(clients.router,   prefix="/api/v1/clients",   tags=["Clients"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(actions.router,   prefix="/api/v1/actions",   tags=["Actions"])


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "online", "version": "1.0.0"}
