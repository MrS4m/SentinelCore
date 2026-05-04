"""
SentinelCore - Modelos do Banco de Dados
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from db.database import Base


# ------------------------------------------------------------------ #
#  ENUMS                                                               #
# ------------------------------------------------------------------ #

class SeverityLevel(str, enum.Enum):
    INFO     = "INFO"
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    OPEN       = "OPEN"
    ACK        = "ACK"        # Reconhecido
    RESOLVED   = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class ActionStatus(str, enum.Enum):
    PENDING   = "PENDING"
    SENT      = "SENT"
    EXECUTED  = "EXECUTED"
    FAILED    = "FAILED"


# ------------------------------------------------------------------ #
#  CLIENTE                                                             #
# ------------------------------------------------------------------ #

class Client(Base):
    __tablename__ = "clients"

    id:         Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name:       Mapped[str] = mapped_column(String(200), nullable=False)
    email:      Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    phone:      Mapped[str | None] = mapped_column(String(30))
    plan:       Mapped[str] = mapped_column(String(50), default="basic")
    is_active:  Mapped[bool] = mapped_column(Boolean, default=True)
    api_token:  Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    settings:   Mapped[dict] = mapped_column(JSON, default=dict)  # configs por cliente
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    agents: Mapped[list["Agent"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="client")


# ------------------------------------------------------------------ #
#  AGENTE                                                              #
# ------------------------------------------------------------------ #

class Agent(Base):
    __tablename__ = "agents"

    id:           Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id:    Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False)
    agent_id:     Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # fingerprint
    hostname:     Mapped[str] = mapped_column(String(200))
    os:           Mapped[str] = mapped_column(String(50))
    os_version:   Mapped[str | None] = mapped_column(String(100))
    arch:         Mapped[str | None] = mapped_column(String(20))
    version:      Mapped[str] = mapped_column(String(20), default="1.0.0")
    is_online:    Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen:    Mapped[datetime | None] = mapped_column(DateTime)
    first_seen:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    risk_score:   Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    tags:         Mapped[list] = mapped_column(JSON, default=list)

    # Relacionamentos
    client: Mapped["Client"] = relationship(back_populates="agents")
    events: Mapped[list["Event"]] = relationship(back_populates="agent")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="agent")


# ------------------------------------------------------------------ #
#  EVENTO (dado bruto enviado pelo agente)                             #
# ------------------------------------------------------------------ #

class Event(Base):
    __tablename__ = "events"

    id:           Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id:     Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    client_id:    Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False)
    event_type:   Mapped[str] = mapped_column(String(50))   # logs, network, processes, ports, cve
    raw_data:     Mapped[dict] = mapped_column(JSON)         # dados brutos do agente
    processed:    Mapped[bool] = mapped_column(Boolean, default=False)
    received_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relacionamentos
    agent: Mapped["Agent"] = relationship(back_populates="events")


# ------------------------------------------------------------------ #
#  ALERTA (gerado pela análise de IA)                                  #
# ------------------------------------------------------------------ #

class Alert(Base):
    __tablename__ = "alerts"

    id:               Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id:        Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False)
    agent_id:         Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    event_id:         Mapped[str | None] = mapped_column(ForeignKey("events.id"))

    # Classificação
    title:            Mapped[str] = mapped_column(String(300))
    severity:         Mapped[SeverityLevel] = mapped_column(SAEnum(SeverityLevel))
    category:         Mapped[str] = mapped_column(String(100))   # brute_force, malware, cve, etc.
    status:           Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus), default=AlertStatus.OPEN)

    # Análise da IA
    description:      Mapped[str] = mapped_column(Text)          # o que aconteceu
    ai_analysis:      Mapped[str | None] = mapped_column(Text)   # análise detalhada da IA
    remediation:      Mapped[str | None] = mapped_column(Text)   # como corrigir
    ai_model_used:    Mapped[str | None] = mapped_column(String(50))

    # Dados técnicos
    source_ip:        Mapped[str | None] = mapped_column(String(45))
    affected_asset:   Mapped[str | None] = mapped_column(String(200))
    cve_ids:          Mapped[list] = mapped_column(JSON, default=list)
    raw_evidence:     Mapped[dict] = mapped_column(JSON, default=dict)
    risk_score:       Mapped[float] = mapped_column(Float, default=0.0)

    # Automação
    auto_remediated:  Mapped[bool] = mapped_column(Boolean, default=False)
    notified:         Mapped[bool] = mapped_column(Boolean, default=False)
    n8n_triggered:    Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at:       Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at:      Mapped[datetime | None] = mapped_column(DateTime)
    acked_by:         Mapped[str | None] = mapped_column(String(200))

    # Relacionamentos
    client: Mapped["Client"] = relationship(back_populates="alerts")
    agent:  Mapped["Agent"] = relationship(back_populates="alerts")
    actions: Mapped[list["RemoteAction"]] = relationship(back_populates="alert")


# ------------------------------------------------------------------ #
#  AÇÃO REMOTA                                                         #
# ------------------------------------------------------------------ #

class RemoteAction(Base):
    __tablename__ = "remote_actions"

    id:          Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id:    Mapped[str | None] = mapped_column(ForeignKey("alerts.id"))
    agent_id:    Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50))   # block_ip, kill_process, etc.
    params:      Mapped[dict] = mapped_column(JSON, default=dict)
    status:      Mapped[ActionStatus] = mapped_column(SAEnum(ActionStatus), default=ActionStatus.PENDING)
    result:      Mapped[dict] = mapped_column(JSON, default=dict)
    triggered_by: Mapped[str] = mapped_column(String(50), default="auto")  # auto, manual, n8n
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relacionamentos
    alert: Mapped["Alert | None"] = relationship(back_populates="actions")
