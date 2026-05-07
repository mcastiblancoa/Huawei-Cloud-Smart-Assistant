# Huawei Cloud Smart Assistant

AI-powered Cloud Operations Assistant for Huawei Cloud. Interact via voice or chat to manage infrastructure, query resources, generate reports, and execute administrative operations using KooCLI.

---

## Architecture

```
/
├── frontend/              React 18 + Vite (Voice & Chat UI)
├── backend/
│   ├── app.py             FastAPI entrypoint
│   ├── config/            Centralized settings & structured logging
│   ├── api/               API routes (chat, voice, health)
│   ├── agents/            LangGraph agent (graph, nodes, prompts)
│   ├── tools/             LangChain tools (KooCLI + discovery)
│   ├── koocli/            KooCLI executor, param flattening, regions
│   ├── schemas/           Dynamic Service Registry + 90+ JSON schemas
│   ├── models/            Pydantic schemas + LangGraph state
│   ├── services/          Voice (SIS, Whisper), Billing (BSS), Resources (RMS), Intent
│   ├── validators/        Parameter validation + destructive op detection
│   ├── memory/            LangGraph checkpointer
│   ├── auth/              Credential management
│   ├── utils/             Retry logic, input sanitization
│   └── requirements.txt
├── .env                   Environment configuration
└── package.json           Monorepo scripts
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **KooCLI-exclusive** | All cloud operations go through `hcloud` CLI — no Terraform |
| **Dynamic Service Registry** | 90+ service schemas loaded at runtime; agent discovers capabilities without hardcoding |
| **LangGraph agent** | ReAct pattern: chatbot → tools → chatbot with MemorySaver checkpointing |
| **Clean Architecture** | Each module has a single responsibility; no cross-layer coupling |
| **Structured logging** | JSON logs in production, dev-friendly format in local |
| **Input sanitization** | All user inputs sanitized before KooCLI execution |
| **Destructive op detection** | Delete/destroy operations flagged for confirmation |

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- [KooCLI](https://support.huaweicloud.com/intl/en-us/qs-hcli/hcli_02_003.html) (`hcloud` in PATH)
- ffmpeg (for voice transcription)

### 1. Environment

Create `.env` in the project root:

```env
# Huawei Cloud Credentials
HUAWEI_REGION=ap-southeast-3
HUAWEI_PROJECT_ID=your_project_id
HUAWEI_AK=your_access_key
HUAWEI_SK=your_secret_key
CLOUD_SDK_DOMAIN_ID=your_domain_id

# IAM (for SIS voice transcription)
HUAWEI_IAM_ENDPOINT=https://iam.ap-southeast-3.myhuaweicloud.com
HUAWEI_SIS_ENDPOINT=https://sis-ext.ap-southeast-3.myhuaweicloud.com
HUAWEI_USERNAME=your_username
HUAWEI_DOMAIN_NAME=your_domain
HUAWEI_PASSWORD=your_password

# SIS Config
SIS_PROPERTY=english_16k_common
SIS_ADD_PUNC=yes
SIS_DIGIT_NORM=yes
SIS_NEED_WORD_INFO=no

# MaaS (DeepSeek via ModelArts)
MAAS_API_KEY=your_maas_api_key
MAAS_API_URL=https://api-ap-southeast-1.modelarts-maas.com/v2/chat/completions
OPEN_API_BASE=https://api-ap-southeast-1.modelarts-maas.com/openai/v1

# Backend
APP_NAME=Huawei Smart Assistant
APP_ENV=local
BACKEND_CORS_ORIGINS=http://localhost:5173
BACKEND_PORT=8003

# Frontend
VITE_API_BASE_URL=http://localhost:8003
WHISPER_ASR_URL=http://your-whisper-host:9000/asr
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8003
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Access at http://localhost:5173

---

## Usage

**Voice Module** — Record in English or Spanish to query resources and billing:
- "Show me my active services"
- "How much did I spend in March 2026?"
- "¿Cuánto gasté en marzo de 2026?"

**Chat Module** — Full infrastructure management via LangGraph + KooCLI:
- "List all my ECS instances"
- "Create a new VPC named my-vpc with CIDR 10.0.0.0/16"
- "Show my billing summary"
- "Delete server abc-123"

---

## Agent Flow

```
User Input → Chatbot Node (DeepSeek + System Prompt)
  → Tool Selection (resolve_schema / get_details / run_koocli)
    → KooCLI Execution (hcloud CLI)
      → Result Parsing → Response to User
```

The agent uses 5 tools:
1. `list_available_services` — Discover 90+ Huawei Cloud services
2. `list_service_operations` — List operations for a service
3. `get_operation_details` — Get required/optional parameters
4. `resolve_service_schema` — Direct schema lookup
5. `run_koocli_command` — Execute `hcloud` commands
