# FinanceAI architecture proposal

## 1. Architectural style

FinanceAI uses a modular monolith in a monorepo. A single FastAPI application is split by business capability, while Next.js is a separate deployable frontend. This is easier to run, test, and explain than premature microservices, without coupling business modules together.

```text
apps/web (presentation)
    -> versioned REST API
apps/api
    -> api routes (HTTP concerns)
    -> application services (use cases and authorization)
    -> domain rules (deterministic business logic)
    -> repositories/adapters (PostgreSQL, AI, files, ERP)
PostgreSQL + pgvector
```

Future background processing should start as an explicit worker process sharing application services. A queue is introduced only when document processing latency or retries justify it.

## 2. Recommended repository structure

```text
finance-ai/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/v1/          # versioned HTTP routers
│   │   │   ├── core/            # config, security, logging
│   │   │   ├── db/              # engine, sessions, base, migrations later
│   │   │   └── modules/         # auth, invoices, documents, AI, etc. later
│   │   └── tests/
│   └── web/
│       └── src/
│           ├── app/             # routes and layouts
│           ├── components/      # reusable UI
│           └── lib/             # typed API clients and utilities
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

`packages/` is intentionally omitted now. It becomes useful only when there is genuinely shared JavaScript code, such as a generated API client or design system. Python and TypeScript should not pretend to share domain models manually; an OpenAPI-generated client can become the contract later.

## 3. Main database entities

All tenant-owned tables carry `company_id`, and repositories must require tenant context. UUID primary keys avoid guessable sequential identifiers in public APIs.

| Entity | Purpose | Important relationships |
| --- | --- | --- |
| Company | Tenant boundary | owns users, suppliers, cost centers, invoices, and knowledge documents |
| User | Authenticated person | belongs to company; has a role |
| Supplier | Vendor master data | belongs to company; referenced by invoices |
| CostCenter | Accounting allocation | belongs to company; referenced by invoices |
| Invoice | Payable/expense | belongs to company, supplier, and optionally cost center/document |
| FinancialDocument | Uploaded invoice evidence | belongs to company and uploader; has extraction status |
| ExtractionReview | AI output plus human corrections | belongs to document and reviewer; preserves audit trail |
| KnowledgeDocument | Internal policy/manual | belongs to company; owns chunks |
| KnowledgeChunk | Embedded text with source metadata | belongs to knowledge document; stores vector and page/section |
| Anomaly | Explainable rule result | belongs to company and related invoice |
| AuditEvent | Security/business audit trail | captures actor, action, target, and safe metadata |
| IntegrationConnection | External system configuration | company-scoped ERP adapter selection and sync state |

Recommended constraints include unique `(company_id, supplier.document_number)`, unique `(company_id, cost_center.code)`, and a carefully defined invoice duplicate key. Money uses `NUMERIC`, never floating point. All timestamps are timezone-aware UTC.

## 4. Authentication and authorization flow

1. The user submits email and password to `POST /api/v1/auth/login`.
2. The API verifies an Argon2id password hash and active company membership.
3. It returns a short-lived access JWT and sets a rotated refresh token in an `HttpOnly`, `Secure`, `SameSite` cookie.
4. The web app keeps the access token in memory and sends it as a bearer token; it never stores refresh tokens in JavaScript-accessible storage.
5. FastAPI resolves a typed `CurrentUser` dependency containing `user_id`, `company_id`, and role.
6. Route-level role checks protect coarse permissions; services enforce resource ownership and company scope.
7. Logout revokes the refresh-token family and clears the cookie.

Roles (`admin`, `finance`, `manager`) are a first release policy, not hard-coded throughout routes. A central permission map keeps authorization testable. Company identity always comes from the authenticated principal, never from a request-controlled `company_id`.

## 5. AI layer

AI providers live behind application-owned interfaces:

```text
API route -> use case -> AI gateway -> OpenAI adapter
                       -> safe finance tools -> repositories
                       -> retrieval service -> pgvector repository
```

- `DocumentExtractionService` extracts native text/OCR input, asks for a strict structured response, validates it with Pydantic, and creates a review draft. It never persists an invoice before human confirmation.
- `FinanceAssistantService` exposes an allowlist of typed, company-scoped tools. The model chooses a tool but never receives database credentials or arbitrary SQL capability.
- `KnowledgeService` retrieves company-scoped chunks and refuses source-dependent answers when citations are insufficient.
- `AIClient` centralizes timeouts, retries, model configuration, token/latency metadata, redaction, and provider substitution.

Prompts contain language instructions and context, not permissions, calculations, or financial rules. Validation, totals, date ranges, anomaly thresholds, and tenant isolation remain deterministic code.

## 6. pgvector strategy

Phase 9 enables the `vector` extension through Alembic and adds an embedding column to `knowledge_chunks`. Each chunk stores normalized text, document ID, page, section, chunk index, content hash, embedding model, dimensions, and embedding.

Retrieval always filters by `company_id` before similarity ranking. Start with cosine distance and a conservative top-k, then optionally add keyword/full-text ranking for hybrid retrieval. An HNSW index is useful after representative data exists; indexing parameters should not be guessed before measuring. Re-embedding is versioned by model and content hash. Citations are assembled from stored metadata, and the assistant must abstain when the retrieved evidence is weak.

## 7. Where LangGraph adds value

LangGraph belongs in the assistant orchestration phase, after individual tools and retrieval are independently working:

```text
classify intent
  -> finance tools | knowledge retrieval | document-status help
  -> validate tool result/evidence
  -> compose cited response
```

Its value is explicit state, branching, validation, retries, and traceability—not multiple personas. The graph will have a small number of deterministic nodes and one shared state schema. CRUD, extraction validation, calculations, and anomaly rules do not need LangGraph.

## 8. MVP definition

The portfolio MVP is complete when a recruiter can:

1. sign in to a seeded tenant;
2. manage suppliers, cost centers, and invoices;
3. see a meaningful six-month dashboard;
4. upload one PDF/image and review structured extraction before saving;
5. ask a controlled financial question and see which safe tool produced the answer;
6. ask a policy question and receive page-level citations;
7. inspect explainable anomaly flags;
8. run the entire demo with one Docker Compose command.

ERP synchronization and LangGraph polish strengthen the portfolio but do not block the first demonstrable MVP.

## 9. Incremental delivery plan

### Phase 1 — foundation (current)

- Create monorepo, environment contract, Dockerfiles, and Compose stack.
- Add Next.js shell, versioned FastAPI routes, structured request logging, and database readiness check.
- Verify lint, type checking, build, API, web, and PostgreSQL connectivity.

### Phase 2 — persistence

- Add SQLAlchemy models and repositories for companies, users, suppliers, cost centers, and invoices.
- Configure Alembic and initial constraints/indexes.
- Add deterministic seed command with tenant-safe fictional data.

### Phase 3 — authentication

- Implement password hashing, JWT access/refresh flow, role dependencies, and audit events.
- Add login UI and protected layout.

### Phase 4 — core CRUD

- Implement typed supplier, cost center, and invoice APIs.
- Add pagination, filtering, validation, tenant-scoped tests, and management screens.

### Phase 5 — dashboard

- Build aggregation queries, KPI endpoint, charts, date filters, and rule-based insights.

### Phase 6 — uploads

- Validate MIME signature, extension, size, hashes, and storage adapter.
- Add upload lifecycle and secure download authorization.

### Phase 7 — AI extraction

- Add text/OCR adapters, Pydantic structured output, confidence fields, review workflow, mocks, and telemetry.

### Phase 8 — financial assistant

- Implement typed safe tools, tool selection, controlled execution, conversational response, and auditability.

### Phase 9 — RAG

- Add pgvector migration, chunking, embedding jobs, tenant-filtered retrieval, citations, and abstention.

### Phase 10 — anomalies

- Implement duplicate, historical deviation, proximity, and cost-center growth rules with explainable outputs.

### Phase 11 — LangGraph

- Compose the proven assistant/retrieval tools into a small routed, validated graph with tracing.

### Phase 12 — ERP adapter

- Add mock external endpoints, adapter interface, idempotent sync, checkpoints, and integration logs.

### Phase 13 — test hardening

- Expand service, route, permission, integration, and AI-contract tests; add CI and coverage thresholds.

### Phase 14 — interface polish

- Complete responsive states, accessibility, empty/error/loading states, and visual consistency.

### Phase 15 — portfolio release

- Capture screenshots, finalize diagrams and ADRs, publish API examples, and prepare GitHub release notes.

## 10. Cross-cutting decisions

- REST is versioned under `/api/v1`; `/docs` exposes OpenAPI in development.
- Logs are structured JSON and include method, path, status, and duration without request/response bodies.
- Upload bytes and AI inputs are not logged.
- Secrets remain server-side and are documented only as empty/example values.
- External integrations use adapter interfaces so the mock ERP can be replaced without changing use cases.
- Async database access is used because AI/document workflows are I/O-heavy, while business rules stay ordinary synchronous functions where appropriate.

