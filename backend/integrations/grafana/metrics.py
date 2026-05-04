"""
SentinelCore - Integração Grafana
Envia métricas via Prometheus Pushgateway para dashboards em tempo real
"""

import logging
from datetime import datetime

import aiohttp

from config.settings import get_settings

logger = logging.getLogger("sentinelcore.grafana")
settings = get_settings()

PUSHGATEWAY_URL = "http://localhost:9091"  # Prometheus Pushgateway


class GrafanaMetrics:

    async def push_alert_metric(self, alert):
        """Envia métricas do alerta para o Pushgateway."""
        severity = str(alert.severity.value) if hasattr(alert.severity, "value") else str(alert.severity)
        hostname = alert.affected_asset or "unknown"
        category = alert.category or "other"

        # Formato Prometheus text exposition
        metrics = (
            f'# HELP sentinelcore_alert_total Total de alertas gerados\n'
            f'# TYPE sentinelcore_alert_total counter\n'
            f'sentinelcore_alert_total{{severity="{severity}",category="{category}",host="{hostname}"}} 1\n\n'

            f'# HELP sentinelcore_risk_score Score de risco do host\n'
            f'# TYPE sentinelcore_risk_score gauge\n'
            f'sentinelcore_risk_score{{host="{hostname}",category="{category}"}} {alert.risk_score}\n\n'

            f'# HELP sentinelcore_auto_remediated Alertas com auto-remediação\n'
            f'# TYPE sentinelcore_auto_remediated counter\n'
            f'sentinelcore_auto_remediated{{host="{hostname}"}} {1 if alert.auto_remediated else 0}\n'
        )

        job = f"sentinelcore_{hostname.replace('.', '_').replace('-', '_')}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{PUSHGATEWAY_URL}/metrics/job/{job}",
                    data=metrics,
                    headers={"Content-Type": "text/plain"},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status in (200, 202):
                        logger.debug(f"Métricas enviadas ao Pushgateway: {job}")
        except Exception as e:
            logger.debug(f"Pushgateway indisponível: {e}")

    async def push_agent_heartbeat(self, hostname: str, risk_score: float, is_online: bool):
        """Envia heartbeat do agente (usado para o dashboard de status)."""
        metrics = (
            f'sentinelcore_agent_online{{host="{hostname}"}} {1 if is_online else 0}\n'
            f'sentinelcore_agent_risk{{host="{hostname}"}} {risk_score}\n'
            f'sentinelcore_agent_last_seen{{host="{hostname}"}} {int(datetime.utcnow().timestamp())}\n'
        )

        job = f"heartbeat_{hostname.replace('.', '_')}"
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{PUSHGATEWAY_URL}/metrics/job/{job}",
                    data=metrics,
                    headers={"Content-Type": "text/plain"},
                    timeout=aiohttp.ClientTimeout(total=3),
                )
        except Exception:
            pass  # heartbeat é best-effort
