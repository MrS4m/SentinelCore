"""
SentinelCore - Motor de IA
Claude API (principal) + Ollama com RAG local (fallback/especializado)
"""
import json
import logging
from datetime import datetime
from typing import Optional

import aiohttp

from config.settings import get_settings

logger = logging.getLogger("sentinelcore.ai")
settings = get_settings()

SYSTEM_PROMPT = """Voce e o SentinelCore AI, um analista senior de seguranca da informacao especializado em PMEs.
Analise eventos de seguranca e retorne APENAS JSON valido, sem markdown.
"""

ANALYSIS_PROMPT_TEMPLATE = """Analise este evento de seguranca e retorne APENAS JSON valido:

HOSTNAME: {hostname}
OS: {os}
TIMESTAMP: {timestamp}

DADOS COLETADOS:
{data}

Retorne exatamente neste formato JSON:
{{
  "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
  "category": "brute_force|malware|cve|port_exposure|suspicious_process|network_anomaly|privilege_escalation|other",
  "title": "Titulo curto do alerta",
  "description": "O que aconteceu",
  "ai_analysis": "Analise tecnica detalhada",
  "remediation": "Passos para corrigir",
  "risk_score": 5.0,
  "auto_actions": [],
  "cve_ids": [],
  "requires_immediate_action": false
}}"""


class AIEngine:
    _claude_client = None
    _rag_engine = None

    @classmethod
    async def initialize(cls):
        """Inicializa clientes de IA."""
        # Claude
        if settings.anthropic_api_key:
            try:
                import anthropic
                cls._claude_client = anthropic.AsyncAnthropic(
                    api_key=settings.anthropic_api_key
                )
                logger.info("Claude API conectado")
            except ImportError:
                logger.warning("anthropic nao instalado")
        else:
            logger.warning("ANTHROPIC_API_KEY nao configurada - usando Ollama ou regras")

        # RAG (opcional)
        if settings.rag_enabled:
            try:
                cls._rag_engine = RAGEngine()
                await cls._rag_engine.initialize()
                logger.info("RAG Engine inicializado")
            except Exception as e:
                logger.warning(f"RAG nao disponivel: {e}")
                cls._rag_engine = None

    @classmethod
    async def analyze_event(cls, event_data: dict) -> dict:
        """Analisa evento tentando Claude, depois Ollama, depois regras."""
        prompt = cls._build_prompt(event_data)

        if cls._claude_client:
            result = await cls._analyze_with_claude(prompt)
            if result:
                result["ai_model_used"] = settings.claude_model
                return result

        result = await cls._analyze_with_ollama(prompt, event_data)
        if result:
            result["ai_model_used"] = f"ollama/{settings.ollama_model}"
            return result

        return cls._rule_based_analysis(event_data)

    @classmethod
    async def _analyze_with_claude(cls, prompt: str) -> Optional[dict]:
        try:
            import anthropic
            message = await cls._claude_client.messages.create(
                model=settings.claude_model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text
            return cls._parse_json_response(raw)
        except Exception as e:
            logger.error(f"Claude erro: {e}")
            return None

    @classmethod
    async def _analyze_with_ollama(cls, prompt: str, event_data: dict) -> Optional[dict]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{settings.ollama_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 1024},
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return cls._parse_json_response(data.get("response", ""))
        except Exception as e:
            logger.debug(f"Ollama nao disponivel: {e}")
        return None

    @classmethod
    def _build_prompt(cls, event_data: dict) -> str:
        summary = cls._summarize_event(event_data)
        return ANALYSIS_PROMPT_TEMPLATE.format(
            hostname=event_data.get("hostname", "unknown"),
            os=event_data.get("os", "unknown"),
            timestamp=event_data.get("timestamp", datetime.utcnow().isoformat()),
            data=json.dumps(summary, ensure_ascii=False, indent=2),
        )

    @classmethod
    def _summarize_event(cls, event_data: dict) -> dict:
        data = event_data.get("data", {})
        summary = {}
        logs = data.get("logs", [])
        alert_logs = [l for l in logs if l.get("has_alert") or l.get("threats")]
        if alert_logs:
            summary["log_alerts"] = alert_logs[:5]
        net = data.get("network", {})
        if net.get("suspicious_outbound"):
            summary["suspicious_connections"] = net["suspicious_outbound"][:3]
        if net.get("high_risk_ports"):
            summary["high_risk_ports"] = net["high_risk_ports"]
        procs = data.get("processes", {})
        if procs.get("suspicious"):
            summary["suspicious_processes"] = procs["suspicious"][:3]
        cves = data.get("cve", {})
        critical_cves = [c for c in cves.get("vulnerabilities", [])
                         if c.get("severity") in ("CRITICAL", "HIGH")]
        if critical_cves:
            summary["critical_cves"] = critical_cves[:3]
        return summary

    @classmethod
    def _parse_json_response(cls, raw: str) -> Optional[dict]:
        if not raw:
            return None
        raw = raw.strip()
        if "```" in raw:
            lines = raw.split("\n")
            raw = "\n".join(l for l in lines if not l.startswith("```"))
        try:
            data = json.loads(raw)
            if {"severity", "title", "description", "remediation"}.issubset(data.keys()):
                return data
        except json.JSONDecodeError:
            pass
        return None

    @classmethod
    def _rule_based_analysis(cls, event_data: dict) -> dict:
        data = event_data.get("data", {})
        severity = "LOW"
        findings = []

        for log in data.get("logs", []):
            if "malware_indicator" in log.get("threats", []):
                severity = "CRITICAL"
                findings.append("Indicador de malware nos logs")
            elif "brute_force" in log.get("threats", []):
                if severity not in ("CRITICAL",):
                    severity = "HIGH"
                findings.append(f"Brute force do IP {log.get('ip', 'desconhecido')}")

        if data.get("processes", {}).get("suspicious"):
            severity = "HIGH" if severity not in ("CRITICAL",) else severity
            findings.append("Processos suspeitos detectados")

        cves = data.get("cve", {})
        if cves.get("critical_count", 0) > 0:
            severity = "CRITICAL"
            findings.append(f"{cves['critical_count']} CVE(s) critico(s)")

        return {
            "severity": severity,
            "category": "other",
            "title": f"Analise automatica - {len(findings)} ocorrencia(s)",
            "description": "\n".join(findings) if findings else "Nenhuma anomalia critica detectada",
            "ai_analysis": "Analise baseada em regras (IA indisponivel)",
            "remediation": "Revise manualmente os dados coletados.",
            "risk_score": {"CRITICAL": 9.0, "HIGH": 7.0, "MEDIUM": 5.0, "LOW": 2.0}.get(severity, 2.0),
            "auto_actions": [],
            "cve_ids": [],
            "requires_immediate_action": severity in ("CRITICAL", "HIGH"),
            "ai_model_used": "rule_based",
        }


class RAGEngine:
    def __init__(self):
        self._collection = None

    async def initialize(self):
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            client = chromadb.PersistentClient(path=settings.chromadb_path)
            self._collection = client.get_or_create_collection(
                name=settings.rag_collection,
            )
            logger.info(f"RAG: {self._collection.count()} documentos na base")
        except ImportError:
            logger.info("chromadb nao instalado - RAG desabilitado")
            raise
        except Exception as e:
            logger.error(f"RAG erro: {e}")
            raise

    async def get_context(self, event_data: dict, n_results: int = 3) -> str:
        if not self._collection:
            return ""
        return ""

    async def add_knowledge(self, documents: list):
        if not self._collection:
            return
        try:
            self._collection.add(
                ids=[doc["id"] for doc in documents],
                documents=[doc["content"] for doc in documents],
                metadatas=[doc.get("metadata", {}) for doc in documents],
            )
        except Exception as e:
            logger.error(f"RAG add erro: {e}")

    async def add_resolved_incident(self, alert: dict, resolution: str):
        doc = {
            "id": f"incident_{alert.get('id', 'unknown')}_{int(datetime.utcnow().timestamp())}",
            "content": (
                f"INCIDENTE: {alert.get('category')} | "
                f"Severidade: {alert.get('severity')} | "
                f"Descricao: {alert.get('description')} | "
                f"Resolucao: {resolution}"
            ),
            "metadata": {
                "type": "resolved_incident",
                "category": alert.get("category"),
                "severity": alert.get("severity"),
            },
        }
        await self.add_knowledge([doc])
