"""
SentinelCore - Integração n8n
Dispara webhooks para automações de resposta a incidentes
"""

import logging
from datetime import datetime

import aiohttp

from config.settings import get_settings

logger = logging.getLogger("sentinelcore.n8n")
settings = get_settings()

# Mapeamento de categoria/severidade para webhook específico do n8n
WEBHOOK_MAP = {
    "brute_force":        "brute-force",
    "malware":            "malware-detected",
    "cve":                "cve-critical",
    "port_exposure":      "port-exposed",
    "suspicious_process": "suspicious-process",
    "network_anomaly":    "network-anomaly",
    "privilege_escalation": "privilege-escalation",
    "default":            "generic-alert",
}


class N8nIntegration:

    async def trigger_alert(self, alert) -> bool:
        """Dispara webhook n8n baseado na categoria do alerta."""
        if not settings.n8n_webhook_base:
            return False

        severity = str(alert.severity.value) if hasattr(alert.severity, "value") else str(alert.severity)

        # Apenas dispara para HIGH e CRITICAL por padrão
        if severity not in ("HIGH", "CRITICAL"):
            return False

        webhook_path = WEBHOOK_MAP.get(alert.category, WEBHOOK_MAP["default"])
        url = f"{settings.n8n_webhook_base}/{webhook_path}"

        payload = {
            "alert_id":        alert.id,
            "severity":        severity,
            "category":        alert.category,
            "title":           alert.title,
            "description":     alert.description,
            "remediation":     alert.remediation,
            "hostname":        alert.affected_asset,
            "source_ip":       alert.source_ip,
            "risk_score":      alert.risk_score,
            "cve_ids":         alert.cve_ids,
            "auto_remediated": alert.auto_remediated,
            "timestamp":       datetime.utcnow().isoformat(),
            # Contexto para o n8n montar a automação
            "suggested_actions": self._suggest_actions(alert),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status in (200, 201):
                        logger.info(f"n8n webhook disparado: {webhook_path}")
                        return True
                    else:
                        logger.warning(f"n8n falhou HTTP {resp.status}: {url}")
                        return False
        except aiohttp.ClientConnectorError:
            logger.warning("n8n não acessível")
            return False
        except Exception as e:
            logger.error(f"Erro n8n: {e}")
            return False

    def _suggest_actions(self, alert) -> list:
        """Sugere ações para o n8n executar com base na categoria."""
        category = alert.category
        severity = str(alert.severity.value) if hasattr(alert.severity, "value") else str(alert.severity)

        actions = []

        if category == "brute_force" and alert.source_ip:
            actions.append({"action": "block_ip",      "ip": alert.source_ip, "reason": "Brute force detectado"})
            actions.append({"action": "ban_fail2ban",   "ip": alert.source_ip})
            actions.append({"action": "notify_ticket",  "priority": "high"})

        elif category == "malware":
            actions.append({"action": "isolate_host",   "reason": "Malware confirmado"})
            actions.append({"action": "collect_forensics"})
            actions.append({"action": "notify_ticket",  "priority": "critical"})

        elif category == "cve":
            actions.append({"action": "notify_ticket",  "priority": "high"})
            actions.append({"action": "schedule_patch", "urgency": "immediate" if severity == "CRITICAL" else "planned"})

        elif category == "port_exposure":
            actions.append({"action": "notify_ticket",  "priority": "medium"})
            actions.append({"action": "schedule_hardening"})

        elif category == "suspicious_process":
            actions.append({"action": "collect_forensics"})
            actions.append({"action": "notify_ticket",  "priority": "high"})

        else:
            actions.append({"action": "notify_ticket",  "priority": "medium"})

        return actions
