"""
SentinelCore - Dispatcher de Notificações
Email (SMTP) + WhatsApp (Evolution API) + Slack + Teams
"""

import logging
import aiohttp
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from config.settings import get_settings

logger = logging.getLogger("sentinelcore.notifications")
settings = get_settings()

SEVERITY_EMOJI = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
    "LOW":      "🟢",
    "INFO":     "⚪",
}


class NotificationDispatcher:
    """Envia alertas para todos os canais configurados."""

    async def send_alert(self, alert, hostname: str):
        """Dispara notificação em todos os canais configurados."""
        tasks = []

        if settings.smtp_host and settings.smtp_user:
            tasks.append(self._send_email(alert, hostname))

        if settings.evolution_api_url and settings.evolution_api_key:
            tasks.append(self._send_whatsapp(alert, hostname))

        if settings.slack_webhook_url:
            tasks.append(self._send_slack(alert, hostname))

        if settings.teams_webhook_url:
            tasks.append(self._send_teams(alert, hostname))

        import asyncio
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Erro na notificação [{i}]: {result}")

    # ---------------------------------------------------------------- #
    #  EMAIL                                                             #
    # ---------------------------------------------------------------- #

    async def _send_email(self, alert, hostname: str):
        """Envia email HTML formatado com os detalhes do alerta."""
        severity = str(alert.severity.value) if hasattr(alert.severity, 'value') else str(alert.severity)
        emoji = SEVERITY_EMOJI.get(severity, "⚠️")

        # Destinatários: email do cliente + admin
        recipients = []
        if hasattr(alert, 'client') and alert.client and alert.client.email:
            recipients.append(alert.client.email)
        if not recipients:
            logger.warning("Email: nenhum destinatário configurado")
            return

        subject = f"{emoji} SentinelCore [{severity}]: {alert.title}"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
    .header {{ background: {'#dc2626' if severity == 'CRITICAL' else '#ea580c' if severity == 'HIGH' else '#ca8a04'}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
    .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
    .section {{ background: white; padding: 15px; margin: 10px 0; border-radius: 6px; border-left: 4px solid #6366f1; }}
    .footer {{ background: #374151; color: #9ca3af; padding: 15px; font-size: 12px; border-radius: 0 0 8px 8px; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;
              background: {'#fef2f2' if severity == 'CRITICAL' else '#fff7ed'}; color: {'#dc2626' if severity == 'CRITICAL' else '#ea580c'}; }}
  </style>
</head>
<body>
  <div class="header">
    <h2 style="margin:0">{emoji} Alerta de Segurança</h2>
    <p style="margin:5px 0 0 0; opacity:0.9">{alert.title}</p>
  </div>
  <div class="content">
    <p><strong>Host:</strong> {hostname} &nbsp; <strong>Data:</strong> {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC &nbsp; <span class="badge">{severity}</span></p>

    <div class="section">
      <h3 style="margin-top:0">📋 O que aconteceu</h3>
      <p>{alert.description}</p>
    </div>

    <div class="section">
      <h3 style="margin-top:0">🔍 Análise Técnica</h3>
      <p>{alert.ai_analysis or 'Análise automática em andamento.'}</p>
    </div>

    <div class="section">
      <h3 style="margin-top:0">🛠️ Como corrigir</h3>
      <p style="white-space: pre-line">{alert.remediation or 'Aguardando análise.'}</p>
    </div>

    {"<div class='section'><h3 style='margin-top:0'>✅ Ação automática executada</h3><p>O sistema executou medidas de contenção automaticamente.</p></div>" if alert.auto_remediated else ""}
  </div>
  <div class="footer">
    <p style="margin:0">SentinelCore Security Platform • ID do alerta: {alert.id}</p>
    <p style="margin:5px 0 0 0">Para ver o dashboard completo: <a href="{settings.grafana_url}" style="color:#818cf8">Grafana Dashboard</a></p>
  </div>
</body>
</html>
"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                use_tls=False,
                start_tls=True,
            )
            logger.info(f"Email enviado para: {recipients}")
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")

    # ---------------------------------------------------------------- #
    #  WHATSAPP (Evolution API)                                          #
    # ---------------------------------------------------------------- #

    async def _send_whatsapp(self, alert, hostname: str):
        """Envia mensagem WhatsApp via Evolution API."""
        severity = str(alert.severity.value) if hasattr(alert.severity, 'value') else str(alert.severity)
        emoji = SEVERITY_EMOJI.get(severity, "⚠️")

        # Número do cliente (deve estar no settings do cliente)
        phone = None
        if hasattr(alert, 'client') and alert.client:
            phone = alert.client.phone

        if not phone:
            logger.warning("WhatsApp: telefone do cliente não cadastrado")
            return

        # Formata número para o padrão Evolution API (ex: 5511999999999)
        phone_clean = "".join(filter(str.isdigit, phone))
        if not phone_clean.startswith("55"):
            phone_clean = f"55{phone_clean}"

        message = (
            f"{emoji} *SENTINELCORE ALERTA [{severity}]*\n\n"
            f"🖥️ *Host:* {hostname}\n"
            f"📌 *Evento:* {alert.title}\n\n"
            f"📋 *O que aconteceu:*\n{alert.description[:300]}\n\n"
            f"🛠️ *Ação necessária:*\n{(alert.remediation or '')[:300]}\n\n"
            f"{'✅ _Contenção automática aplicada_' if alert.auto_remediated else '⚡ _Ação manual necessária_'}\n\n"
            f"_ID: {alert.id[:8]}_"
        )

        payload = {
            "number":  phone_clean,
            "text":    message,
            "options": {"delay": 1200},
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{settings.evolution_api_url}/message/sendText/{settings.evolution_instance}",
                    json=payload,
                    headers={
                        "apikey":       settings.evolution_api_key,
                        "Content-Type": "application/json",
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status in (200, 201):
                        logger.info(f"WhatsApp enviado para: {phone_clean}")
                    else:
                        body = await resp.text()
                        logger.warning(f"WhatsApp falhou HTTP {resp.status}: {body[:200]}")
        except Exception as e:
            logger.error(f"Erro ao enviar WhatsApp: {e}")

    # ---------------------------------------------------------------- #
    #  SLACK                                                             #
    # ---------------------------------------------------------------- #

    async def _send_slack(self, alert, hostname: str):
        """Envia mensagem formatada no Slack via Incoming Webhook."""
        severity = str(alert.severity.value) if hasattr(alert.severity, 'value') else str(alert.severity)
        color = {"CRITICAL": "#dc2626", "HIGH": "#ea580c", "MEDIUM": "#ca8a04"}.get(severity, "#6b7280")

        payload = {
            "attachments": [{
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"{SEVERITY_EMOJI.get(severity, '⚠️')} [{severity}] {alert.title}"}
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Host:*\n{hostname}"},
                            {"type": "mrkdwn", "text": f"*Categoria:*\n{alert.category}"},
                            {"type": "mrkdwn", "text": f"*Risk Score:*\n{alert.risk_score:.1f}/10"},
                            {"type": "mrkdwn", "text": f"*Auto-remediado:*\n{'✅ Sim' if alert.auto_remediated else '❌ Não'}"},
                        ]
                    },
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*O que aconteceu:*\n{alert.description[:500]}"}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*Como corrigir:*\n{(alert.remediation or '')[:500]}"}},
                    {"type": "divider"},
                    {"type": "context", "elements": [{"type": "mrkdwn", "text": f"SentinelCore • ID: `{alert.id[:8]}` • {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC"}]},
                ]
            }]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.slack_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        logger.info("Slack: notificação enviada")
                    else:
                        logger.warning(f"Slack falhou: HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Erro Slack: {e}")

    # ---------------------------------------------------------------- #
    #  TEAMS                                                             #
    # ---------------------------------------------------------------- #

    async def _send_teams(self, alert, hostname: str):
        """Envia card adaptativo no Microsoft Teams."""
        severity = str(alert.severity.value) if hasattr(alert.severity, 'value') else str(alert.severity)
        color = {"CRITICAL": "attention", "HIGH": "warning", "MEDIUM": "accent"}.get(severity, "default")

        payload = {
            "@type":    "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": {"CRITICAL": "dc2626", "HIGH": "ea580c", "MEDIUM": "ca8a04"}.get(severity, "6b7280"),
            "summary":  f"SentinelCore [{severity}]: {alert.title}",
            "sections": [
                {
                    "activityTitle":    f"{SEVERITY_EMOJI.get(severity, '⚠️')} **[{severity}] {alert.title}**",
                    "activitySubtitle": f"Host: {hostname} • {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC",
                    "facts": [
                        {"name": "Categoria",     "value": alert.category},
                        {"name": "Risk Score",    "value": f"{alert.risk_score:.1f}/10"},
                        {"name": "Auto-remediado","value": "✅ Sim" if alert.auto_remediated else "❌ Não"},
                        {"name": "ID do Alerta",  "value": alert.id[:8]},
                    ],
                    "text": f"**O que aconteceu:** {alert.description[:400]}\n\n**Como corrigir:** {(alert.remediation or '')[:400]}",
                }
            ],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.teams_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        logger.info("Teams: notificação enviada")
                    else:
                        logger.warning(f"Teams falhou: HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Erro Teams: {e}")
