# 🛡️ SentinelCore — Guia de Implantação no Windows (Docker)

---

## 📦 O QUE VOCÊ VAI RECEBER

Após seguir este guia, você terá rodando na sua máquina:

| Serviço | Endereço | O que é |
|---|---|---|
| **Frontend** (Dashboard) | http://localhost:5173 | Interface visual |
| **Backend** (API) | http://localhost:8000 | Servidor principal |
| **Docs da API** | http://localhost:8000/docs | Documentação automática |
| **Grafana** | http://localhost:3000 | Painéis de métricas |
| **n8n** | http://localhost:5678 | Automação de fluxos |

---

## ✅ PRÉ-REQUISITOS

Confirme que tem instalado (se não tiver, instale antes de continuar):

- **Docker Desktop** → https://www.docker.com/products/docker-desktop
- **Chave da API Anthropic (Claude)** → https://console.anthropic.com *(necessária para a IA funcionar)*

---

## 📁 PASSO 1 — Monte a pasta do projeto

Crie uma pasta chamada `sentinelcore` em algum lugar fácil de achar.
Por exemplo: `C:\Users\SeuNome\Desktop\sentinelcore`

Dentro dela, você deve ter esta estrutura **exatamente assim**:

```
sentinelcore/
├── docker-compose.yml       ← arquivo que você vai baixar abaixo
├── .env                     ← arquivo que você vai baixar abaixo
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── .env
│   └── src/
│       ├── main.jsx
│       └── SentinelCoreDashboard.jsx   ← seu arquivo original
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py
    ├── prometheus/
    │   └── prometheus.yml
    └── (demais pastas do zip)
```

### Como extrair o backend:
1. Pegue o arquivo `sentinelcore-backend.zip`
2. Clique com botão direito → **Extrair aqui** (ou "Extrair para...")
3. Renomeie a pasta extraída de `sentinelcore-backend` para `backend`
4. Coloque essa pasta `backend` dentro da sua pasta `sentinelcore`

### Os outros arquivos (frontend):
Coloque os arquivos baixados nos lugares indicados acima:
- `docker-compose.yml` → na raiz de `sentinelcore/`
- `.env` → na raiz de `sentinelcore/`
- `Dockerfile`, `package.json`, `vite.config.js`, `index.html`, `.env` → dentro de `sentinelcore/frontend/`
- `main.jsx` → dentro de `sentinelcore/frontend/src/`
- `SentinelCoreDashboard.jsx` → dentro de `sentinelcore/frontend/src/`

---

## 🔑 PASSO 2 — Configure sua chave da API

1. Abra o arquivo `.env` que está na raiz de `sentinelcore/` com o **Bloco de Notas**
2. Encontre esta linha:
   ```
   ANTHROPIC_API_KEY=sk-ant-COLOQUE-SUA-CHAVE-AQUI
   ```
3. Substitua `sk-ant-COLOQUE-SUA-CHAVE-AQUI` pela sua chave real
4. Salve o arquivo

> ⚠️ **IMPORTANTE:** O arquivo deve se chamar `.env` (com ponto na frente, sem extensão .txt).
> Se o Windows não deixar criar assim, no terminal use: `rename .env.txt .env`

---

## 🐳 PASSO 3 — Abra o terminal na pasta certa

1. Abra a pasta `sentinelcore` no Explorador de Arquivos
2. Clique na **barra de endereço** (onde aparece o caminho da pasta)
3. Digite `cmd` e pressione **Enter**
4. Um terminal preto vai abrir já dentro da pasta certa

---

## ✅ PASSO 4 — Verifique se o Docker está funcionando

No terminal, digite este comando e pressione Enter:

```
docker --version
```

**Resultado esperado:** algo como `Docker version 24.x.x`

Se aparecer erro, abra o **Docker Desktop** (procure o ícone da baleia 🐳 na bandeja do sistema, canto inferior direito) e espere ele iniciar completamente antes de tentar de novo.

---

## 🚀 PASSO 5 — Suba o projeto!

No terminal (ainda dentro da pasta `sentinelcore`), digite:

```
docker compose up -d --build
```

**O que vai acontecer:**
- O Docker vai baixar as imagens necessárias *(na primeira vez pode levar 5–15 minutos)*
- Vai compilar o backend e o frontend
- Vai iniciar todos os serviços

**Como saber que terminou?** O cursor vai voltar para você digitar. Você pode acompanhar com:

```
docker compose logs -f backend
```

Quando aparecer `Application startup complete`, o backend está pronto!
Pressione `Ctrl + C` para sair dos logs (não para o projeto).

---

## 🌐 PASSO 6 — Acesse no navegador

Abra o Chrome ou Edge e acesse:

| O que | Endereço |
|---|---|
| 🖥️ **Dashboard principal** | http://localhost:5173 |
| 🔧 **API do backend** | http://localhost:8000 |
| 📖 **Documentação da API** | http://localhost:8000/docs |
| 📊 **Grafana** (métricas) | http://localhost:3000 |
| ⚙️ **n8n** (automação) | http://localhost:5678 |

**Login do Grafana:** usuário `admin` / senha `sentinel123`
**Login do n8n:** usuário `admin` / senha `sentinel123`

---

## 🛑 COMO PARAR O PROJETO

Para parar tudo quando não precisar mais:

```
docker compose down
```

Para subir de novo depois:

```
docker compose up -d
```

*(sem o `--build` nas próximas vezes — só use `--build` quando mudar os arquivos)*

---

## ❗ ERROS COMUNS E SOLUÇÕES

### "port is already allocated" (porta já em uso)
Algum programa está usando a mesma porta. Verifique se não há outro Docker rodando ou feche o programa que usa aquela porta.

### "Cannot connect to the Docker daemon"
O Docker Desktop não está aberto. Abra-o e espere a baleia aparecer na bandeja do sistema.

### Frontend não carrega
Aguarde mais uns segundos — o npm install dentro do container demora um pouco na primeira vez. Tente recarregar a página após 1–2 minutos.

### Backend com erro de banco de dados
Certifique-se de que o container `postgres` está saudável. Verifique com:
```
docker compose ps
```
Todos devem mostrar `running` ou `healthy`.

---

## 🔍 COMANDOS ÚTEIS

| Comando | Para que serve |
|---|---|
| `docker compose ps` | Ver status de todos os serviços |
| `docker compose logs backend` | Ver erros do backend |
| `docker compose logs frontend` | Ver erros do frontend |
| `docker compose restart backend` | Reiniciar só o backend |
| `docker compose down -v` | Para tudo E apaga os dados *(cuidado!)* |

---

*Guia gerado para o projeto SentinelCore — versão local para testes*
