"""
SentinelCore Backend - Configuracoes Centrais
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "SentinelCore"
    debug: bool = False
    secret_key: str = "TROQUE-POR-UMA-CHAVE-SECRETA-FORTE-EM-PRODUCAO"

    # --- Banco de dados ---
    database_url: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinelcore"
    redis_url: str = "redis://localhost:6379/0"

    # --- IA: Claude (Anthropic) ---
    anthropic_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4-20250514"

    # --- IA: Ollama (local) ---
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_rag_model: str = "llama3.2"
    rag_enabled: bool = True
    rag_collection: str = "sentinel_knowledge"
    chromadb_path: str = "./data/chromadb"

    # --- Notificacoes: Email ---
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: str = "alertas@sentinelcore.com"

    # --- Notificacoes: WhatsApp ---
    evolution_api_url: Optional[str] = None
    evolution_api_key: Optional[str] = None
    evolution_instance: Optional[str] = None

    # --- Notificacoes: Slack / Teams ---
    slack_webhook_url: Optional[str] = None
    teams_webhook_url: Optional[str] = None

    # --- Grafana ---
    grafana_url: str = "http://localhost:3000"
    grafana_api_key: Optional[str] = None
    grafana_password: str = "sentinel123"          # senha admin do Grafana

    # --- n8n ---
    n8n_webhook_base: Optional[str] = None
    n8n_password: str = "sentinel123"              # senha admin do n8n
    n8n_encryption_key: str = "mude-esta-chave-em-producao-32ch"

    # --- Seguranca ---
    token_expire_hours: int = 24 * 30
    rate_limit_per_minute: int = 120

    # --- CORS ---
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:80",
        "http://localhost",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",          # ignora variaveis extras do .env sem quebrar
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
