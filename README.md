# FinanceAI

FinanceAI is a portfolio-grade B2B financial operations platform designed to demonstrate practical full-stack engineering, automation, and responsible AI integration.

> Current status: **Phase 11 — LangGraph orchestration complete**. The platform now includes authentication, financial operations, dashboard analytics, protected uploads, human-reviewed extraction, safe assistants, cited RAG, explainable anomaly detection, and a validated multi-route workflow.

## Why this project exists

This project demonstrates AI applied to real financial workflows—not a generic chatbot. The planned product combines reviewed document extraction, controlled financial query tools, source-grounded internal knowledge retrieval, and explainable anomaly detection. Deterministic rules remain in application code; AI is reserved for interpretation, extraction, classification, routing, and summarization.

## Architecture at a glance

```text
Browser -> Next.js web -> FastAPI /api/v1 -> PostgreSQL + pgvector
                              |
                              +-> AI gateway (future)
                              +-> ERP adapter (future)
```

- `apps/web`: Next.js App Router, React, TypeScript, and Tailwind CSS.
- `apps/api`: FastAPI, Pydantic Settings, async SQLAlchemy, and asyncpg.
- `docs`: architecture decisions, data model, AI boundaries, MVP, and delivery plan.
- `docker-compose.yml`: local web, API, and pgvector-enabled PostgreSQL stack.

The full proposal is documented in [docs/architecture.md](docs/architecture.md).

## Quick start with Docker

Requirements: Docker Desktop with Docker Compose.

```bash
cp .env.example .env
docker compose up --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.db.seed
```

On PowerShell, use `Copy-Item .env.example .env` instead of `cp` if desired.

Open:

- Web: http://localhost:3000
- Authenticated workspace: http://localhost:3000/workspace
- API docs: http://localhost:8000/docs
- API liveness: http://localhost:8000/api/v1/health
- API/database readiness: http://localhost:8000/api/v1/health/ready

Stop the stack with `docker compose down`. Add `--volumes` only when you intentionally want to delete local database data.

## Run without Docker (application processes)

Keep PostgreSQL running through `docker compose up -d db`, then:

```powershell
# API
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:DATABASE_URL="postgresql+asyncpg://finance_ai:finance_ai_dev@localhost:5432/finance_ai"
uvicorn app.main:app --reload

# Web (in another terminal, from the repository root)
npm install
npm run dev:web
```

## Quality checks

```bash
npm run lint:web
npm run typecheck:web
npm run build:web

cd apps/api
ruff check .
pytest
```

## Database lifecycle

Apply all pending migrations and load the fictional demonstration dataset:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.db.seed
```

The seed is idempotent and creates one fictional company, three demo users, 20 suppliers, five cost centers, and 100 invoices covering six months. Demo passwords are hashed with Argon2id and are intended only for local development.

## Demo authentication

The seed creates three development-only accounts. Their password comes from `DEMO_USER_PASSWORD` and defaults to `FinanceAI123!` in the example environment.

| Email | Role |
| --- | --- |
| `admin@aurora.demo` | admin |
| `finance@aurora.demo` | finance |
| `manager@aurora.demo` | manager |

Authentication endpoints:

- `POST /api/v1/auth/login` — validates credentials and sets a rotating refresh cookie.
- `POST /api/v1/auth/refresh` — rotates the refresh token and issues a new access token.
- `POST /api/v1/auth/logout` — revokes the complete refresh-token family.
- `GET /api/v1/auth/me` — returns the authenticated user.
- `GET /api/v1/auth/users` — tenant-scoped user list restricted to admins.

Refresh token values are never stored directly. Only SHA-256 digests are persisted. Production mode requires a non-default JWT secret and enables `Secure` cookies.

## Financial operations and dashboard

Authenticated users can read company-scoped data. The `admin` and `finance` roles can create, update, and delete financial records; `manager` remains read-only.

- `/api/v1/suppliers` — supplier CRUD with search, status filters, and pagination.
- `/api/v1/cost-centers` — cost center CRUD with search and pagination.
- `/api/v1/invoices` — invoice CRUD with financial and date validation plus operational filters.
- `/api/v1/dashboard` — KPIs, upcoming due dates, breakdowns, evolution, and deterministic insights.

The workspace at `/workspace` consumes these APIs with an access token kept only in browser memory. Session recovery uses the rotating HttpOnly refresh cookie.

## Secure document upload

`POST /api/v1/documents` accepts PDF, PNG, and JPEG files up to the configured limit (10 MB by default). The API validates the extension, declared media type, and binary signature; computes SHA-256; rejects duplicates within the company; generates its own storage key; and prevents path traversal. Metadata is stored in PostgreSQL and file contents live in the persistent `document_data` Docker volume.

Relevant settings:

- `DOCUMENT_STORAGE_PATH` — private storage directory used by the API.
- `MAX_UPLOAD_SIZE_MB` — maximum accepted file size.

## AI document extraction

Uploaded documents can be processed through `POST /api/v1/documents/{id}/extract`. PDFs are sent as file inputs and PNG/JPEG documents as vision inputs. The provider must return a Pydantic-validated structured result containing supplier, document number, amount, dates, description, category, and suggested cost center.

Extraction never creates an invoice by itself. The document moves to `review`, the user corrects the suggested fields in the workspace, and only `POST /api/v1/documents/{id}/confirm` persists an invoice with `source=document` and the recorded confidence score.

Configuration:

- `AI_PROVIDER=demo` provides a deterministic zero-cost portfolio demonstration.
- `AI_PROVIDER=openai` and a valid `OPENAI_API_KEY` enable OpenAI Responses API extraction.
- `OPENAI_MODEL` selects the vision-capable model; the example uses `gpt-4o-mini`.

AI telemetry records provider/model latency and token counts without logging document content.

## Secure financial assistant

`POST /api/v1/ai/chat` accepts natural-language financial questions and routes each request through a small allowlist of read-only tools:

- `get_upcoming_payments`
- `get_overdue_invoices`
- `get_expenses_by_period`
- `get_top_suppliers`
- `get_cost_center_summary`
- `compare_monthly_expenses`

Every query is scoped by the authenticated user's `company_id`; the model never receives database credentials or unrestricted SQL access. Tool inputs have controlled date ranges and result limits. With `AI_PROVIDER=demo`, a deterministic intent router and response formatter keep the complete feature demonstrable without external API costs. With `AI_PROVIDER=openai`, the Responses API selects strict function tools and summarizes only their controlled output.

## Roadmap

The project is developed in deliberately small phases. Phases 1–11 cover foundation, persistence, authentication, financial operations, dashboard analytics, secure document ingestion, human-reviewed AI extraction, safe assistants, cited RAG, explainable anomaly detection, and LangGraph orchestration. See [docs/architecture.md](docs/architecture.md) for the complete task breakdown.

### Phase 9 knowledge base

- Administrators can index searchable PDF or TXT policies and manuals.
- Text is split into page-aware chunks and stored as 1536-dimensional vectors in PostgreSQL/pgvector.
- Queries are always tenant-scoped and ranked with cosine similarity.
- Knowledge answers include document, relevant excerpt, page (when available), and similarity.
- If no source is relevant, the assistant abstains instead of generating an unsupported answer.
- `AI_PROVIDER=demo` uses local deterministic embeddings; `AI_PROVIDER=openai` uses `text-embedding-3-small` by default.

### Phase 10 anomaly detection

- Deterministic rules detect supplier amount spikes, repeated document numbers, close duplicate payments, and abnormal cost-center growth.
- Every finding stores severity, explanation, calculated metrics, related invoice, status, and detection time.
- Detection is idempotent and tenant-scoped; administrators and finance users can execute scans.
- The dashboard anomaly count is backed by persisted findings.
- “Analyze with AI” summarizes an already-calculated finding and recommends human checks without making payment decisions.
- `AI_PROVIDER=demo` produces a deterministic executive summary, while OpenAI mode uses the Responses API with `store=false`.

### Phase 11 LangGraph orchestration

The unified assistant uses a deliberately small state graph:

`intent router → finance tools | RAG | anomalies | document guidance → response validator`

- The router is deterministic and sends each request to exactly one specialist.
- The finance node reuses tenant-scoped, read-only tools; it never generates SQL.
- The RAG node can answer only with cited internal sources or safely abstain.
- The anomaly node summarizes persisted findings, and the document node preserves mandatory upload and human review.
- Every route passes through a final validator that checks its safety contract.
- The API returns the execution trace so the workflow is demonstrable and auditable in the UI.

