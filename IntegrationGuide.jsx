import { useState } from "react";

const C = {
  bg:      "#0f1117", panel:   "#161b26", panelAlt:"#0a0d14",
  border:  "#1e2535", wine:    "#7b2d3e", wineL:   "#9e3a50",
  navy:    "#1a3a6b", navyL:   "#2251a3", blue:    "#3b72c4",
  blueL:   "#5a9de8", teal:    "#2d8f8f", green:   "#22c55e",
  amber:   "#f59e0b", red:     "#ef4444", text:    "#e2e8f0",
  textMid: "#94a3b8", textDim: "#475569", pink:    "#c45a7a",
};

const SECTIONS = [
  {
    id: "overview",
    icon: "🗺️",
    title: "Visão Geral da Arquitetura",
    color: C.blue,
    content: [
      {
        type: "diagram",
        label: "Fluxo completo de dados",
        code: `
┌─────────────────────────────────────────────────────────┐
│                    CLIENTE (PME)                        │
│  ┌──────────────────────────────────┐                   │
│  │   SentinelCore Agent (Python)    │                   │
│  │   Coleta: logs, rede, CVEs...    │                   │
│  └──────────────┬───────────────────┘                   │
└─────────────────┼───────────────────────────────────────┘
                  │ POST /api/v1/events
                  │ Bearer: {client_token}
                  ▼
┌─────────────────────────────────────────────────────────┐
│             SENTINELCORE BACKEND (FastAPI)               │
│                                                         │
│  /api/v1/agents    → registra agentes                   │
│  /api/v1/events    → recebe dados do agente             │
│  /api/v1/alerts    → CRUD de alertas                    │
│  /api/v1/dashboard → resumo executivo                   │
│  /api/v1/actions   → ações remotas                      │
│                                                         │
│  Motor IA: Claude API → Ollama+RAG → Regras             │
└──────────┬──────────────────────────┬───────────────────┘
           │ REST API                 │ Webhooks
           ▼                          ▼
┌─────────────────┐        ┌─────────────────────┐
│  FRONTEND React │        │  n8n / Grafana       │
│  (Dashboard)    │        │  (Automação/Métricas)│
└─────────────────┘        └─────────────────────┘`,
      },
    ],
  },
  {
    id: "setup",
    icon: "⚙️",
    title: "1. Setup Inicial",
    color: C.teal,
    content: [
      {
        type: "step",
        label: "Instalar dependências do frontend",
        code: `# Crie o projeto React (Vite recomendado — mais rápido)
npm create vite@latest sentinelcore-frontend -- --template react
cd sentinelcore-frontend

# Instale as dependências necessárias
npm install axios                    # chamadas HTTP para o backend
npm install recharts                 # gráficos (já usado no dashboard)
npm install react-router-dom         # navegação entre páginas
npm install @tanstack/react-query    # cache e sincronização de dados
npm install socket.io-client         # WebSocket para dados em tempo real`,
      },
      {
        type: "step",
        label: "Criar arquivo .env com a URL do backend",
        code: `# frontend/.env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# Em produção:
# VITE_API_URL=https://api.sentinelcore.seudominio.com`,
      },
    ],
  },
  {
    id: "client",
    icon: "🔌",
    title: "2. Cliente HTTP (Axios)",
    color: C.navyL,
    content: [
      {
        type: "code",
        label: "src/api/client.js — configuração base do Axios",
        code: `import axios from "axios";

// Instância base do Axios com URL e headers padrão
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL + "/api/v1",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Interceptor de REQUEST — injeta o token automaticamente
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("sentinel_token");
  if (token) {
    config.headers.Authorization = \`Bearer \${token}\`;
  }
  return config;
});

// Interceptor de RESPONSE — trata erros globalmente
api.interceptors.response.use(
  (response) => response.data,  // retorna só o .data
  (error) => {
    if (error.response?.status === 401) {
      // Token expirado → redireciona para login
      localStorage.removeItem("sentinel_token");
      window.location.href = "/login";
    }
    return Promise.reject(error.response?.data || error.message);
  }
);

export default api;`,
      },
    ],
  },
  {
    id: "services",
    icon: "📦",
    title: "3. Services (uma função por endpoint)",
    color: C.wine,
    content: [
      {
        type: "code",
        label: "src/api/services.js — todos os endpoints mapeados",
        code: `import api from "./client";

// ── DASHBOARD ─────────────────────────────────────────
export const dashboardService = {
  // GET /api/v1/dashboard/summary
  getSummary: () => api.get("/dashboard/summary"),
};

// ── AGENTES ───────────────────────────────────────────
export const agentsService = {
  // GET /api/v1/agents
  list: () => api.get("/agents"),

  // POST /api/v1/agents/register
  register: (data) => api.post("/agents/register", data),
};

// ── ALERTAS ───────────────────────────────────────────
export const alertsService = {
  // GET /api/v1/alerts?severity=HIGH&status=OPEN
  list: (params = {}) => api.get("/alerts", { params }),

  // GET /api/v1/alerts/:id
  get: (id) => api.get(\`/alerts/\${id}\`),

  // PATCH /api/v1/alerts/:id/ack
  ack: (id) => api.patch(\`/alerts/\${id}/ack\`),

  // PATCH /api/v1/alerts/:id/resolve
  resolve: (id, description) =>
    api.patch(\`/alerts/\${id}/resolve\`, { description }),
};

// ── AÇÕES REMOTAS ─────────────────────────────────────
export const actionsService = {
  // POST /api/v1/actions
  dispatch: (agentHostname, actionType, params = {}, reason = "") =>
    api.post("/actions", {
      agent_hostname: agentHostname,
      action_type:    actionType,
      params,
      reason,
    }),
};

// ── CLIENTES ──────────────────────────────────────────
export const clientsService = {
  // POST /api/v1/clients
  create: (data) => api.post("/clients", data),

  // GET /api/v1/clients
  list: () => api.get("/clients"),
};`,
      },
    ],
  },
  {
    id: "hooks",
    icon: "🪝",
    title: "4. React Query Hooks (cache automático)",
    color: C.pink,
    content: [
      {
        type: "code",
        label: "src/hooks/useDashboard.js",
        code: `import { useQuery } from "@tanstack/react-query";
import { dashboardService } from "../api/services";

// Hook para o resumo do dashboard
// Atualiza automaticamente a cada 30 segundos
export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn:  dashboardService.getSummary,
    refetchInterval: 30_000,       // polling a cada 30s
    staleTime:       10_000,       // considera fresco por 10s
  });
}`,
      },
      {
        type: "code",
        label: "src/hooks/useAlerts.js",
        code: `import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { alertsService } from "../api/services";

// Lista alertas com filtros opcionais
export function useAlerts(filters = {}) {
  return useQuery({
    queryKey: ["alerts", filters],
    queryFn:  () => alertsService.list(filters),
    refetchInterval: 15_000,  // atualiza a cada 15s
  });
}

// Mutação para reconhecer (ACK) um alerta
export function useAckAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => alertsService.ack(id),
    onSuccess: () => {
      // Invalida o cache → força re-fetch da lista
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });
}

// Mutação para resolver um alerta
export function useResolveAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, description }) =>
      alertsService.resolve(id, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });
}`,
      },
      {
        type: "code",
        label: "src/hooks/useAgents.js",
        code: `import { useQuery } from "@tanstack/react-query";
import { agentsService } from "../api/services";

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn:  agentsService.list,
    refetchInterval: 20_000,  // verifica status online/offline a cada 20s
  });
}`,
      },
    ],
  },
  {
    id: "integration",
    icon: "🔗",
    title: "5. Integrando no Dashboard",
    color: C.amber,
    content: [
      {
        type: "code",
        label: "Substituir dados simulados por dados reais no SentinelCoreDashboard.jsx",
        code: `// No topo do SentinelCoreDashboard.jsx, substitua os imports:

// ANTES (dados simulados):
// const [logs, setLogs] = useState(generateLogs);
// const [sources, setSources] = useState(...);

// DEPOIS (dados reais do backend):
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useDashboardSummary } from "./hooks/useDashboard";
import { useAlerts }          from "./hooks/useAlerts";
import { useAgents }          from "./hooks/useAgents";

// Envolva o app com o QueryClientProvider em main.jsx:
// const queryClient = new QueryClient();
// <QueryClientProvider client={queryClient}>
//   <SIEMDashboard />
// </QueryClientProvider>

export default function SIEMDashboard() {
  // ── Dados do backend ──────────────────────────────
  const { data: summary, isLoading: loadingSummary } =
    useDashboardSummary();

  const { data: alerts = [], isLoading: loadingAlerts } =
    useAlerts({ status: "OPEN" });

  const { data: agents = [], isLoading: loadingAgents } =
    useAgents();

  // ── KPI Cards com dados reais ─────────────────────
  // Substitua os valores fixos:
  // value={fmt(totalLogs)}  →  value={fmt(summary?.total_logs ?? 0)}
  // value={eps}             →  value={summary?.eps ?? 0}
  // value="5/6"             →  value={\`\${summary?.agents?.online}/\${summary?.agents?.total}\`}
  // value="47"              →  value={summary?.alerts_24h?.open ?? 0}

  // ── Lista de alertas reais ─────────────────────────
  // Substitua RECENT_EVENTS por:
  const recentEvents = alerts.slice(0, 8).map((a) => ({
    time:  new Date(a.created_at).toLocaleTimeString("pt-BR"),
    host:  a.affected_asset ?? "desconhecido",
    ip:    a.source_ip ?? "—",
    type:  a.category?.toUpperCase() ?? "OTHER",
    sev:   a.severity,
    msg:   a.description,
    id:    a.id,
  }));

  // ── Lista de agentes reais ─────────────────────────
  // Substitua o array AGENTS por:
  const agentsList = agents.map((a) => ({
    name:   a.hostname,
    os:     a.os,
    status: a.is_online ? "online" : "offline",
    risk:   Math.round(a.risk_score),
    ip:     a.agent_id,
    cpu:    0,   // virá de métricas futuras
    mem:    0,
    disk:   0,
  }));

  // ── Loading state ─────────────────────────────────
  if (loadingSummary && loadingAgents) {
    return (
      <div style={{ background:"#0f1117", minHeight:"100vh",
                    display:"flex", alignItems:"center",
                    justifyContent:"center", color:"#e2e8f0" }}>
        ⏳ Carregando dados do SentinelCore...
      </div>
    );
  }

  // ... resto do componente igual, usando recentEvents e agentsList
}`,
      },
    ],
  },
  {
    id: "websocket",
    icon: "⚡",
    title: "6. WebSocket — Dados em Tempo Real",
    color: C.green,
    content: [
      {
        type: "step",
        label: "Adicionar WebSocket no backend (main.py)",
        code: `# Instale no backend:
pip install python-socketio

# Em main.py, adicione:
import socketio
from fastapi import FastAPI

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# No alert_processor.py, após criar o alerta, emita evento:
await sio.emit("new_alert", {
    "id":       alert.id,
    "severity": severity_str,
    "title":    alert.title,
    "host":     event_data.get("hostname"),
})

# Em uvicorn, suba socket_app ao invés de app:
# uvicorn main:socket_app --host 0.0.0.0 --port 8000`,
      },
      {
        type: "code",
        label: "src/hooks/useWebSocket.js — ouvir alertas em tempo real",
        code: `import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { io } from "socket.io-client";

let socket = null;

export function useRealtimeAlerts() {
  const queryClient = useQueryClient();

  useEffect(() => {
    // Conecta ao WebSocket do backend
    socket = io(import.meta.env.VITE_WS_URL, {
      auth: { token: localStorage.getItem("sentinel_token") },
    });

    // Novo alerta recebido em tempo real
    socket.on("new_alert", (alert) => {
      console.log("🔔 Novo alerta:", alert.severity, alert.title);

      // Invalida cache → componentes atualizam automaticamente
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });

      // Notificação nativa do navegador
      if (Notification.permission === "granted" &&
          ["CRITICAL","HIGH"].includes(alert.severity)) {
        new Notification(\`🔴 SentinelCore [\${alert.severity}]\`, {
          body: \`\${alert.host}: \${alert.title}\`,
          icon: "/shield-icon.png",
        });
      }
    });

    // Atualização de status de agente
    socket.on("agent_status", (data) => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    });

    return () => {
      socket?.disconnect();
      socket = null;
    };
  }, [queryClient]);
}

// Use no componente raiz:
// function SIEMDashboard() {
//   useRealtimeAlerts();   // ← adicione esta linha
//   ...
// }`,
      },
    ],
  },
  {
    id: "auth",
    icon: "🔐",
    title: "7. Autenticação (Login)",
    color: C.wineL,
    content: [
      {
        type: "code",
        label: "src/pages/Login.jsx — tela de login simples",
        code: `import { useState } from "react";
import api from "../api/client";

export default function Login({ onLogin }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    setLoading(true);
    setError("");
    try {
      // Testa o token fazendo uma chamada ao dashboard
      // O backend valida o Bearer token e retorna os dados
      await api.get("/dashboard/summary", {
        headers: { Authorization: \`Bearer \${token}\` },
      });

      // Token válido → salva e redireciona
      localStorage.setItem("sentinel_token", token);
      onLogin();
    } catch {
      setError("Token inválido ou sem permissão.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ background:"#0f1117", minHeight:"100vh",
                  display:"flex", alignItems:"center",
                  justifyContent:"center" }}>
      <div style={{ background:"#161b26", border:"1px solid #1e2535",
                    borderRadius:12, padding:40, width:360 }}>
        <h2 style={{ color:"#e2e8f0", marginBottom:24 }}>
          🛡️ SentinelCore
        </h2>
        <input
          type="password"
          placeholder="Cole seu API Token aqui"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleLogin()}
          style={{ width:"100%", padding:"10px 14px", borderRadius:6,
                   border:"1px solid #1e2535", background:"#0f1117",
                   color:"#e2e8f0", fontSize:13, marginBottom:12 }}
        />
        {error && (
          <p style={{ color:"#ef4444", fontSize:12, marginBottom:12 }}>
            {error}
          </p>
        )}
        <button
          onClick={handleLogin}
          disabled={loading || !token}
          style={{ width:"100%", padding:"10px", borderRadius:6,
                   border:"none", background:"#7b2d3e", color:"#fff",
                   fontSize:13, fontWeight:700, cursor:"pointer" }}>
          {loading ? "Verificando..." : "Entrar"}
        </button>
      </div>
    </div>
  );
}`,
      },
    ],
  },
  {
    id: "main",
    icon: "🚀",
    title: "8. main.jsx — Juntando tudo",
    color: C.blue,
    content: [
      {
        type: "code",
        label: "src/main.jsx",
        code: `import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import SIEMDashboard from "./SentinelCoreDashboard";
import Login from "./pages/Login";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
});

function App() {
  const [authed, setAuthed] = useState(
    () => !!localStorage.getItem("sentinel_token")
  );

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <SIEMDashboard />
    </QueryClientProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);`,
      },
    ],
  },
  {
    id: "cors",
    icon: "🌐",
    title: "9. CORS no Backend",
    color: C.teal,
    content: [
      {
        type: "code",
        label: "config/settings.py — libere a URL do frontend",
        code: `# Em config/settings.py, ajuste cors_origins:

class Settings(BaseSettings):
    cors_origins: list[str] = [
        "http://localhost:5173",    # Vite dev server
        "http://localhost:3000",    # alternativa
        "https://app.sentinelcore.seudominio.com",  # produção
    ]

# O middleware já está configurado em main.py:
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.cors_origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )`,
      },
    ],
  },
  {
    id: "deploy",
    icon: "📦",
    title: "10. Build e Deploy",
    color: C.navyL,
    content: [
      {
        type: "step",
        label: "Build de produção do frontend",
        code: `# Gera os arquivos estáticos em /dist
npm run build

# Teste local do build
npm run preview`,
      },
      {
        type: "step",
        label: "Servir o frontend via Nginx (mesmo servidor do backend)",
        code: `# /etc/nginx/sites-available/sentinelcore
server {
    listen 80;
    server_name app.sentinelcore.seudominio.com;

    # Frontend React (arquivos estáticos)
    root /var/www/sentinelcore/dist;
    index index.html;

    # React Router — redireciona tudo para index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy reverso para o backend FastAPI
    location /api/ {
        proxy_pass         http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }

    # WebSocket (Socket.IO)
    location /socket.io/ {
        proxy_pass         http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
    }
}`,
      },
      {
        type: "step",
        label: "Script de deploy automatizado",
        code: `#!/bin/bash
# deploy.sh — roda no servidor

echo "🚀 Deploy SentinelCore Frontend..."

# 1. Atualiza código
git pull origin main

# 2. Instala dependências e faz build
cd frontend
npm ci
npm run build

# 3. Copia para pasta do Nginx
cp -r dist/* /var/www/sentinelcore/dist/

# 4. Reinicia Nginx
nginx -t && systemctl reload nginx

echo "✅ Frontend publicado com sucesso!"`,
      },
    ],
  },
  {
    id: "checklist",
    icon: "✅",
    title: "Checklist de Integração",
    color: C.green,
    content: [
      {
        type: "checklist",
        items: [
          { done: true,  text: "Backend FastAPI rodando em localhost:8000" },
          { done: true,  text: "Banco PostgreSQL + Redis ativos (docker compose up -d)" },
          { done: false, text: "Criar cliente no backend: POST /api/v1/clients" },
          { done: false, text: "Copiar api_token retornado para o .env do frontend" },
          { done: false, text: "Configurar VITE_API_URL no .env do frontend" },
          { done: false, text: "npm install no frontend" },
          { done: false, text: "Substituir dados simulados pelos hooks React Query" },
          { done: false, text: "Testar login com o token no browser" },
          { done: false, text: "Instalar agente em um servidor de teste" },
          { done: false, text: "Confirmar que alertas aparecem no dashboard" },
          { done: false, text: "Configurar WebSocket para updates em tempo real" },
          { done: false, text: "Configurar SMTP/WhatsApp para notificações" },
          { done: false, text: "Build de produção + Nginx configurado" },
        ],
      },
    ],
  },
];

// ─── Componentes de conteúdo ──────────────────────────────────────────

function CodeBlock({ code, label }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(code.trim());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <div style={{ marginBottom: 16 }}>
      {label && (
        <div style={{ fontSize: 11, color: C.textDim, marginBottom: 6,
                      fontFamily: "monospace", letterSpacing: .3 }}>
          📄 {label}
        </div>
      )}
      <div style={{ position: "relative" }}>
        <pre style={{ background: "#070a0f", border: `1px solid ${C.border}`,
                      borderRadius: 8, padding: "16px 20px", overflow: "auto",
                      fontSize: 12, lineHeight: 1.7, color: "#c9d1d9",
                      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                      margin: 0, maxHeight: 420 }}>
          <code>{code.trim()}</code>
        </pre>
        <button onClick={copy}
          style={{ position: "absolute", top: 10, right: 10,
                   padding: "4px 10px", borderRadius: 4, border: "none",
                   background: copied ? C.green : C.border,
                   color: copied ? "#fff" : C.textMid,
                   fontSize: 10, cursor: "pointer", transition: "all .2s",
                   fontWeight: 600 }}>
          {copied ? "✓ Copiado!" : "Copiar"}
        </button>
      </div>
    </div>
  );
}

function Checklist({ items }) {
  const [checked, setChecked] = useState(() =>
    items.map(i => i.done)
  );
  const done = checked.filter(Boolean).length;
  const pct = Math.round((done / items.length) * 100);

  return (
    <div>
      {/* Barra de progresso */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between",
                      marginBottom: 6 }}>
          <span style={{ fontSize: 12, color: C.textMid }}>
            Progresso da integração
          </span>
          <span style={{ fontSize: 12, fontWeight: 700,
                         color: pct === 100 ? C.green : C.amber }}>
            {done}/{items.length} — {pct}%
          </span>
        </div>
        <div style={{ height: 6, background: C.bg, borderRadius: 3 }}>
          <div style={{ width: `${pct}%`, height: "100%", borderRadius: 3,
                        background: pct === 100
                          ? `linear-gradient(90deg,${C.green},#4ade80)`
                          : `linear-gradient(90deg,${C.wine},${C.amber})`,
                        transition: "width .4s" }}/>
        </div>
      </div>
      {/* Itens */}
      {items.map((item, i) => (
        <div key={i} onClick={() => setChecked(c => {
          const n = [...c]; n[i] = !n[i]; return n;
        })}
          style={{ display: "flex", alignItems: "flex-start", gap: 10,
                   padding: "8px 10px", borderRadius: 6, cursor: "pointer",
                   marginBottom: 4,
                   background: checked[i] ? "#0f2f1a22" : "transparent",
                   transition: "background .2s" }}>
          <div style={{ width: 18, height: 18, borderRadius: 4, flexShrink: 0,
                        border: `2px solid ${checked[i] ? C.green : C.border}`,
                        background: checked[i] ? C.green : "transparent",
                        display: "flex", alignItems: "center",
                        justifyContent: "center", transition: "all .2s",
                        marginTop: 1 }}>
            {checked[i] && <span style={{ color: "#fff", fontSize: 11, fontWeight:800 }}>✓</span>}
          </div>
          <span style={{ fontSize: 13, color: checked[i] ? C.textDim : C.text,
                         textDecoration: checked[i] ? "line-through" : "none",
                         transition: "all .2s" }}>
            {item.text}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── COMPONENTE PRINCIPAL ────────────────────────────────────────────

export default function IntegrationGuide() {
  const [active, setActive] = useState("overview");
  const section = SECTIONS.find(s => s.id === active);

  return (
    <div style={{ background: C.bg, minHeight: "100vh",
                  fontFamily: "'Barlow', sans-serif", color: C.text,
                  fontSize: 13, display: "flex", flexDirection: "column" }}>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
        * { box-sizing:border-box; margin:0; padding:0; }
        ::-webkit-scrollbar { width:4px; }
        ::-webkit-scrollbar-track { background:${C.bg}; }
        ::-webkit-scrollbar-thumb { background:${C.border}; border-radius:2px; }
        .nav-item:hover { background:${C.border}44 !important; }
      `}</style>

      {/* TOP BAR */}
      <div style={{ background: C.panelAlt, borderBottom: `1px solid ${C.border}`,
                    padding: "12px 28px", display: "flex",
                    alignItems: "center", gap: 14 }}>
        <div style={{ width: 34, height: 34, borderRadius: 8,
                      background: C.wine, display: "flex",
                      alignItems: "center", justifyContent: "center",
                      fontSize: 18 }}>🛡️</div>
        <div>
          <div style={{ fontFamily: "'Barlow Condensed',sans-serif",
                        fontSize: 18, fontWeight: 800, letterSpacing: 1 }}>
            SENTINELCORE
          </div>
          <div style={{ fontSize: 10, color: C.textDim, letterSpacing: 2 }}>
            GUIA DE INTEGRAÇÃO BACKEND ↔ FRONTEND
          </div>
        </div>
      </div>

      <div style={{ display: "flex", flex: 1 }}>

        {/* SIDEBAR */}
        <div style={{ width: 240, background: C.panelAlt,
                      borderRight: `1px solid ${C.border}`,
                      padding: "16px 0", flexShrink: 0,
                      position: "sticky", top: 0, height: "100vh",
                      overflowY: "auto" }}>
          {SECTIONS.map(s => (
            <div key={s.id} className="nav-item" onClick={() => setActive(s.id)}
              style={{ display: "flex", alignItems: "center", gap: 10,
                       padding: "10px 20px", cursor: "pointer",
                       transition: "background .15s",
                       borderLeft: active === s.id
                         ? `3px solid ${s.color}`
                         : "3px solid transparent",
                       background: active === s.id ? `${s.color}18` : "transparent" }}>
              <span style={{ fontSize: 15 }}>{s.icon}</span>
              <span style={{ fontSize: 12, fontWeight: active === s.id ? 700 : 400,
                             color: active === s.id ? s.color : C.textMid,
                             lineHeight: 1.3 }}>
                {s.title}
              </span>
            </div>
          ))}
        </div>

        {/* CONTEÚDO */}
        <div style={{ flex: 1, padding: "28px 36px", overflowY: "auto",
                      maxWidth: 900 }}>

          {/* Header da seção */}
          <div style={{ display: "flex", alignItems: "center", gap: 12,
                        marginBottom: 24 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10,
                          background: `${section.color}22`,
                          border: `1.5px solid ${section.color}`,
                          display: "flex", alignItems: "center",
                          justifyContent: "center", fontSize: 20 }}>
              {section.icon}
            </div>
            <div>
              <h1 style={{ fontFamily: "'Barlow Condensed',sans-serif",
                           fontSize: 24, fontWeight: 800,
                           color: section.color, letterSpacing: .5 }}>
                {section.title}
              </h1>
            </div>
          </div>

          {/* Conteúdo dinâmico */}
          {section.content.map((block, i) => (
            <div key={i}>
              {(block.type === "code" || block.type === "step" || block.type === "diagram") && (
                <CodeBlock code={block.code} label={block.label} />
              )}
              {block.type === "checklist" && (
                <div style={{ background: C.panel,
                              border: `1px solid ${C.border}`,
                              borderRadius: 10, padding: 20 }}>
                  <Checklist items={block.items} />
                </div>
              )}
            </div>
          ))}

          {/* Navegação entre seções */}
          <div style={{ display: "flex", justifyContent: "space-between",
                        marginTop: 32, paddingTop: 20,
                        borderTop: `1px solid ${C.border}` }}>
            {(() => {
              const idx = SECTIONS.findIndex(s => s.id === active);
              const prev = SECTIONS[idx - 1];
              const next = SECTIONS[idx + 1];
              return (<>
                {prev ? (
                  <button onClick={() => setActive(prev.id)}
                    style={{ padding: "8px 18px", borderRadius: 6,
                             border: `1px solid ${C.border}`,
                             background: "transparent", color: C.textMid,
                             cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                    ← {prev.title}
                  </button>
                ) : <div/>}
                {next && (
                  <button onClick={() => setActive(next.id)}
                    style={{ padding: "8px 18px", borderRadius: 6, border: "none",
                             background: section.color, color: "#fff",
                             cursor: "pointer", fontSize: 12, fontWeight: 700 }}>
                    {next.title} →
                  </button>
                )}
              </>);
            })()}
          </div>
        </div>
      </div>
    </div>
  );
}
