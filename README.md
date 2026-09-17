<div align="center">

```
 __      __           _      _             
 \ \    / /          (_)    | |            
  \ \  / /__ _ __ _   _   __| |_   _ _ __  
   \ \/ / _ \ '__| | | | / _` | | | | '_ \ 
    \  /  __/ |  | |_| || (_| | |_| | | | |
     \/ \___|_|   \__,_| \__,_|\__, |_| |_|
                                __/ |      
                               |___/       
```

# ⚡ VERIDYN
### *The Production Reliability & Continuous Verification Harness for AI Agents*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-black?style=for-the-badge&logo=alembic)](https://alembic.sqlalchemy.org/)
[![Status](https://img.shields.io/badge/Build-Passing-brightgreen?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Don't ship AI agents to production on faith. Ship them on mathematical proof.</b><br>
  Veridyn evaluates, regression-tests, and enforces automated deployment gates for LLM & RAG agents before code reaches your users.
</p>

---

<p align="center">
  <a href="#-the-problem">The Problem</a> •
  <a href="#-core-capabilities">Core Capabilities</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-execution-lifecycle">Lifecycle</a> •
  <a href="#-quickstart-guide">Quickstart</a> •
  <a href="#-rest-api-walkthrough">API Walkthrough</a> •
  <a href="#-project-structure">Directory Tree</a> •
  <a href="#-roadmap">Roadmap</a>
</p>

---

</div>

## 📌 The Problem

Traditional CI/CD fails when applied to AI systems:

| Traditional Software CI/CD | Autonomous AI & RAG Agents |
| :--- | :--- |
| **Deterministic**: Input $X$ always returns Output $Y$. | **Stochastic**: Same prompt can produce divergent responses. |
| **Unit tests catch regressions**: Syntax, types, boundary bugs. | **Silent semantic regressions**: Prompt edits cause hallucinations or break JSON tool calls in 8% of edge cases. |
| **Pass/Fail binary assertions**: `assert response.status == 200`. | **Multi-dimensional criteria**: Faithfulness, latency budget, context recall, toxicity, and tool parameter precision. |

> **Veridyn brings software engineering rigor to non-deterministic AI pipelines.** 
> It provides an automated evaluation harness and gatekeeper that blocks regressions before deployment.

---

## 🚀 Core Capabilities

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                       VERIDYN SUITE                             │
    │                                                                 │
    │   [1. Registry]         [2. Test Suite]       [3. Evaluation]   │
    │   Agent & Version  ──>  Golden Datasets  ──>  Latency, Scoring  │
    │   Config Hashes         Edge Scenarios        RAG Triad         │
    │                                                                 │
    │                           │                                     │
    │                           ▼                                     │
    │                                                                 │
    │   [4. Tracing Engine]   [5. Deployment Gate]                    │
    │   Tool Telemetry   ──>  BLOCK / ALLOW                           │
    │   Step-by-step audit    CI/CD Promotion Guard                   │
    └─────────────────────────────────────────────────────────────────┘
```

### 1. 🤖 Agent & Version Registry
- Track agents across any framework: **LangChain**, **LlamaIndex**, **CrewAI**, **AutoGen**, or custom REST endpoints.
- Immutable agent version snapshots tagged with endpoint URLs, config hashes, and model hyperparameters.

### 2. 🧪 Deterministic Benchmark & Test Runner
- Curate golden test datasets with custom input schemas and expected behaviors.
- Concurrent test execution runner with millisecond-accurate latency profiling and failure capture.

### 3. 📊 Evaluation & Metric Engine
- Multi-dimensional scoring: Faithfulness, Answer Relevance, Context Recall, Hallucination Index, and Safety.
- Link evaluation runs to specific agent versions for clear historical regression curves.

### 4. 🛡️ CI/CD Deployment Gates
- Automated threshold verification (e.g., `Faithfulness >= 0.92`, `P95 Latency <= 1500ms`, `Pass Rate == 100%`).
- Emits programmatic pass/fail signals directly into your GitHub Actions / GitLab CI pipelines.

### 5. 🔍 Deep Execution Tracing & Observability
- Granular telemetry capturing input prompts, actual completions, intermediate tool calls, and error traces.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Clients ["Interfaces & CI/CD Layer"]
        CLI["Veridyn CLI"]
        WebUI["Mission Control Dashboard"]
        GHA["GitHub Actions / CI Gatekeeper"]
    end

    subgraph API ["Veridyn Core Platform (FastAPI)"]
        Router["API Gateway / Routers"]
        AuthMiddleware["JWT Security & Tenant Isolation"]
        
        subgraph Services ["Execution & Verification Engine"]
            ExecSvc["Agent Execution Engine"]
            EvalSvc["Evaluation & Metric Service"]
            GateSvc["Deployment Gate Policy Evaluator"]
            TraceSvc["Telemetry & Trace Logger"]
        end
    end

    subgraph Data ["Persistent Storage Layer"]
        Postgres[("PostgreSQL 15+\n(Relational Metadata)")]
        Alembic["Alembic Migration Engine"]
    end

    subgraph AI ["Target Agents Under Test"]
        AgentREST["Agent Endpoint (HTTP/gRPC)"]
        AgentLocal["Python SDK Agent Adapter"]
    end

    Clients -->|REST / Bearer Token| Router
    Router --> AuthMiddleware
    AuthMiddleware --> Services
    
    ExecSvc -->|Dispatches Test Inputs| AI
    AI -->|Completions & Latency| ExecSvc
    
    ExecSvc --> TraceSvc
    TraceSvc --> Postgres
    EvalSvc --> Postgres
    GateSvc --> Postgres
    
    GateSvc -->|Pass / Block Signal| GHA
    Alembic -.->|Schema Versioning| Postgres
```

---

## 🔄 Execution Lifecycle

```
[Agent Code Push] 
       │
       ▼
[Register Agent Version] ──> Generate config hash & snapshot metadata
       │
       ▼
[Trigger Evaluation Suite] ──> Batch test runner executes N test cases
       │
       ├──> Record step latencies (ms)
       ├──> Capture output & tool payloads
       └──> Calculate evaluation score vectors
       │
       ▼
[Evaluate Deployment Gate]
       │
       ├─── Pass: Thresholds met ──> Promote to Staging / Production 🚀
       └─── Fail: Regression detected ──> Halt Pipeline & Alert Team 🛑
```

---

## ⚡ Quickstart Guide

### Prerequisites
- **Python 3.11+**
- **PostgreSQL** instance running locally or via Docker / Supabase / Neon

### 1. Clone & Set Up Environment

```bash
# Clone the repository
git clone https://github.com/souvikx18/RAG-Agent-Eval-Harness.git
cd RAG-Agent-Eval-Harness/veridyn-backend

# Initialize virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt  # or your installed packages (fastapi, uvicorn, sqlalchemy, alembic, pydantic, psycopg2-binary, etc.)
```

### 2. Configure Environment (`.env`)

Create a `.env` file in `veridyn-backend/`:

```env
APP_NAME=Veridyn
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# Database Connection
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/veridyn_db

# Cryptography & Authentication
JWT_SECRET_KEY=generate_a_secure_32_character_random_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 3. Run Database Migrations

```bash
alembic upgrade head
```

### 4. Start the Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- 🌐 **API Base:** `http://127.0.0.1:8000`
- 📑 **Interactive Swagger UI:** `http://127.0.0.1:8000/docs`
- 🩺 **Health Check:** `http://127.0.0.1:8000/health/database`

---

## 📡 REST API Walkthrough

<details>
<summary><b>1. Developer Registration & Authentication</b></summary>

```bash
# Register an account
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "engineer@enterprise.ai",
    "password": "StrongPassword123!",
    "full_name": "AI Reliability Lead"
  }'

# Log in & retrieve Bearer Token
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "engineer@enterprise.ai",
    "password": "StrongPassword123!"
  }'
```
</details>

<details>
<summary><b>2. Register an Agent & Agent Version</b></summary>

```bash
# Register an Agent
curl -X POST http://127.0.0.1:8000/agents \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CustomerSupport-RAG",
    "description": "Enterprise customer assistant with hybrid search",
    "framework": "LangChain"
  }'

# Snapshot a Version
curl -X POST http://127.0.0.1:8000/agents/<AGENT_ID>/versions \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "v1.2.0-rc1",
    "endpoint": "https://agents.internal.net/v1/chat",
    "config_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "description": "Upgraded vector embedding model from bge-small to text-embedding-3-large"
  }'
```
</details>

<details>
<summary><b>3. Define Benchmark Test Cases & Run Evaluations</b></summary>

```bash
# Create a Test Case
curl -X POST http://127.0.0.1:8000/test-cases \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "<AGENT_ID>",
    "input_data": "How do I upgrade my subscription plan to Enterprise?",
    "expected_behavior": "Must cite doc_id=pricing_2026 and output JSON with plan=enterprise"
  }'

# Trigger an Evaluation Run
curl -X POST http://127.0.0.1:8000/evaluations \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_version_id": "<VERSION_ID>",
    "name": "Sprint 34 Regression Harness"
  }'
```
</details>

<details>
<summary><b>4. Check Deployment Gate Pass / Fail</b></summary>

```bash
# Verify Deployment Gate
curl -X GET http://127.0.0.1:8000/deployment-gates/<GATE_ID> \
  -H "Authorization: Bearer <TOKEN>"
```
</details>

---

## 📂 Project Structure

```text
veridyn-backend/
├── alembic.ini                    # Database migration configuration
├── migrations/                    # Alembic revision scripts
│   └── versions/                  # Version migration files
├── app/
│   ├── main.py                    # Application bootstrap & router registration
│   ├── api/                       # REST API endpoint definitions
│   │   ├── auth.py                # User authentication & tokens
│   │   ├── agents.py              # Agent registry CRUD
│   │   ├── agent_versions.py      # Version tagging & config snapshotting
│   │   ├── test_cases.py          # Benchmark test suite definitions
│   │   ├── test_runs.py           # Test execution dispatch & status
│   │   ├── evaluations.py         # Evaluation lifecycle orchestration
│   │   ├── evaluation_results.py  # Granular metric outcome records
│   │   ├── execution_traces.py    # Latency & step telemetry logs
│   │   └── deployment_gates.py    # Production gate validation logic
│   ├── core/                      # Infrastructure & configuration
│   │   ├── config.py              # Environment variables
│   │   ├── database.py            # SQLAlchemy engine & session factory
│   │   ├── dependencies.py        # Dependency injection (Auth, DB)
│   │   └── security.py            # Password hashing & JWT signing
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── agent.py
│   │   ├── agent_version.py
│   │   ├── test_case.py
│   │   ├── test_run.py
│   │   ├── evaluation.py
│   │   ├── evaluation_result.py
│   │   ├── execution_trace.py
│   │   └── deployment_gate.py
│   ├── schemas/                   # Pydantic validation & serialization models
│   └── services/                  # Business logic & background workers
│       ├── agent_execution_service.py
│       ├── evaluation_service.py
│       └── test_run_service.py
```

---

## 🗺️ Roadmap

- [x] **FastAPI Platform Foundation**: Clean architecture, asynchronous ready
- [x] **Multi-Tenant JWT Auth**: Secure developer registration and session tokens
- [x] **Database Schema & Migrations**: Complete relational schema covering runs, traces, and metrics
- [x] **Agent & Version Lifecycle**: REST APIs for agents, versions, test cases, and runs
- [x] **Execution & Evaluation Services**: Test run state machine and latency capture
- [ ] **Automated LLM-as-a-Judge**: Built-in RAG Triad evaluators (Faithfulness, Relevance, Groundedness)
- [ ] **GitHub Action Gate (`veridyn-action`)**: Instant PR checks that prevent faulty agent versions from merging
- [ ] **Telemetry Visualizer Web App**: Next.js dashboard with interactive execution traces and regression charts
- [ ] **Streaming Test Progress**: WebSockets for real-time benchmark visualizer

---

## 🤝 Contributing

We welcome contributions from the AI engineering and open-source community:

1. **Fork** the repository
2. **Create your branch**: `git checkout -b feat/evaluator-enhancements`
3. **Commit changes**: `git commit -m "Add hallucination metric evaluator"`
4. **Push to branch**: `git push origin feat/evaluator-enhancements`
5. **Open a Pull Request**

---

<div align="center">

Made with ☕ and precision for the next generation of AI Engineering.

**[⬆ Back to Top](#-veridyn)**

</div>
