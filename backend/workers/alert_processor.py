"""
SentinelCore - Worker de Processamento de Alertas
Executa em background: IA → Alerta → Notificações → n8n → Auto-remediação
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.ai.engine import AIEngine
from db.database import AsyncSessionLocal
from db.models import Alert, Agent, Event, SeverityLevel, AlertStatus
from integrations.notifications.dispatcher import NotificationDispatcher
from integrations.n8n.webhooks import N8nIntegration
from integrations.grafana.metrics import GrafanaMetrics

logger = logging.getLogger("sentinelcore.workers.alert")


async def process_alert_async(
    event_id:       str,
    event_data:     dict,
    client_id:      str,
    agent_id:       str,
    quick_severity: str,
):
    """
    Pipeline completo de processamento de alerta:
    1. Análise com IA (Claude ou Ollama+RAG)
    2. Persiste alerta no banco
    3. Executa auto-remediação se necessário
    4. Dispara notificações (email, WhatsApp, Slack, Teams)
    5. Aciona webhook n8n para automações
    6. Atualiza métricas no Grafana
    """
    async with AsyncSessionLocal() as db:
        try:
            logger.info(
                f"Iniciando análise IA | Host: {event_data.get('hostname')} | "
                f"Severidade prévia: {quick_severity}"
            )

            # 1. Análise com IA
            analysis = await AIEngine.analyze_event(event_data)

            if not analysis:
                logger.warning("IA não retornou análise válida")
                return

            severity_str = analysis.get("severity", quick_severity)

            # 2. Cria alerta no banco
            alert = Alert(
                client_id=client_id,
                agent_id=agent_id,
                event_id=event_id,
                title=analysis.get("title", "Alerta de segurança"),
                severity=SeverityLevel(severity_str),
                category=analysis.get("category", "other"),
                description=analysis.get("description", ""),
                ai_analysis=analysis.get("ai_analysis", ""),
                remediation=analysis.get("remediation", ""),
                ai_model_used=analysis.get("ai_model_used"),
                risk_score=float(analysis.get("risk_score", 5.0)),
                cve_ids=analysis.get("cve_ids", []),
                raw_evidence=event_data.get("data", {}),
                source_ip=_extract_source_ip(event_data),
                affected_asset=event_data.get("hostname"),
                status=AlertStatus.OPEN,
                created_at=datetime.utcnow(),
            )
            db.add(alert)
            await db.flush()

            # 3. Auto-remediação
            auto_actions = analysis.get("auto_actions", [])
            if auto_actions and analysis.get("requires_immediate_action"):
                await _execute_auto_remediation(db, alert, agent_id, auto_actions)
                alert.auto_remediated = True

            # 4. Notificações
            if severity_str in ("CRITICAL", "HIGH"):
                dispatcher = NotificationDispatcher()
                await dispatcher.send_alert(alert, event_data.get("hostname", ""))
                alert.notified = True

            # 5. Webhook n8n
            n8n = N8nIntegration()
            triggered = await n8n.trigger_alert(alert)
            alert.n8n_triggered = triggered

            # 6. Métricas Grafana
            grafana = GrafanaMetrics()
            await grafana.push_alert_metric(alert)

            # 7. RAG: aprende com o incidente para enriquecer análises futuras
            if severity_str in ("HIGH", "CRITICAL"):
                await AIEngine._rag_engine.add_resolved_incident(
                    {
                        "id":          alert.id,
                        "category":    alert.category,
                        "severity":    severity_str,
                        "description": alert.description,
                    },
                    resolution="Pendente de resolução",
                ) if AIEngine._rag_engine else None

            await db.commit()

            logger.info(
                f"✅ Alerta gerado | ID: {alert.id} | "
                f"Severidade: {severity_str} | Título: {alert.title}"
            )

        except Exception as e:
            logger.error(f"Erro no processamento de alerta: {e}", exc_info=True)
            await db.rollback()


async def _execute_auto_remediation(
    db: AsyncSession,
    alert: Alert,
    agent_db_id: str,
    auto_actions: list,
):
    """Persiste ações de remediação automática para serem enviadas ao agente."""
    from db.models import RemoteAction, ActionStatus

    for action in auto_actions:
        action_type = action.get("type")
        if not action_type:
            continue

        remote_action = RemoteAction(
            alert_id=alert.id,
            agent_id=agent_db_id,
            action_type=action_type,
            params=action.get("params", {}),
            status=ActionStatus.PENDING,
            triggered_by="auto",
            created_at=datetime.utcnow(),
        )
        db.add(remote_action)
        logger.info(f"Auto-ação criada: {action_type} | Motivo: {action.get('reason', '')}")


def _extract_source_ip(event_data: dict) -> str | None:
    """Tenta extrair IP de origem mais relevante dos dados do evento."""
    data = event_data.get("data", {})

    # IPs maliciosos confirmados primeiro
    for ip_info in data.get("network", {}).get("ip_reputation", []):
        if ip_info.get("is_malicious"):
            return ip_info.get("ip")

    # IP de brute force nos logs
    for log in data.get("logs", []):
        if "brute_force" in log.get("threats", []) and log.get("ip"):
            return log["ip"]

    return None
