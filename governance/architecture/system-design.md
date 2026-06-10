# System Design (C2 — Containers)

Traces to: `governance/architecture/system-context.md`, `CLAUDE.md § Technology stack`

---

## Containers

### 1. Frontend — Next.js 15 PWA

| Attribute | Value |
|---|---|
| Technology | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| Deployment | Vercel |
| Installable | PWA (next-pwa, manifest, service worker) — NFR-04 |
| Language | Spanish default, English alternative — NFR-03 |

**Responsibility:** Presentation and user interaction only. No business logic (GR-ARCH-003).

**Modules rendered:**
- Scenario selector / manager (RF-07)
- Operations panel — priority queue + case detail (RF-05)
- Communications generator UI (RF-04.3–RF-04.5)
- Executive panel — KPI dashboard + NL query (RF-06)

**Communicates with:** FastAPI backend via REST/JSON over HTTPS.

---

### 2. Backend API — FastAPI

| Attribute | Value |
|---|---|
| Technology | Python 3.12+, FastAPI, Pydantic, SQLAlchemy |
| Deployment | Railway or Fly.io |
| Architecture | Hexagonal (ports and adapters) — GR-ARCH-004 |
| Schema | OpenAPI auto-generated, validated before merge — GR-ARCH-002 |

**Responsibility:** All business logic — dataset generation, scoring, prioritization, LLM orchestration, audit logging.

**Key sub-systems:**
- Dataset generator (RF-01): procedural layer (NumPy/Faker/Pandas) + LLM enrichment
- Scoring engine (RF-02): feature engineering + ML model (trained on synthetic data)
- Prioritization engine (RF-03): priority value formula + Pareto filter
- Communications service (RF-04): prompt building + OpenRouter call + draft persistence
- NL query service (RF-06.3): NL → structured query → visualization data + narrative

**Communicates with:**
- PostgreSQL (internal, via SQLAlchemy adapter)
- OpenRouter (external, via HTTP adapter)

---

### 3. Database — PostgreSQL

| Attribute | Value |
|---|---|
| Technology | PostgreSQL (latest stable) |
| Migrations | Alembic |
| Access | Only from FastAPI backend — never directly from frontend |

**Stores:** Scenarios, Clients, Invoices, Payments, Scores, Communications, ContactResults.

See `domain-model.md` for entity definitions.

---

### 4. AI Gateway — OpenRouter

| Attribute | Value |
|---|---|
| Protocol | HTTPS, OpenAI-compatible REST |
| Model selection | Per-use-case, read from config — GR-AI-002 |
| Cost strategy | Cost-effective models for data gen / analytics; higher-quality for comms — GR-AI-005 |

**Used for:** LLM enrichment of synthetic data (RF-01.3), communication draft generation (RF-04.2), NL portfolio query (RF-06.3).

---

## Request flows

### Flow 1 — Load priority queue
```
Operator browser
  → GET /api/scenarios/{id}/priority-queue
  → Prioritization engine (reads Scores + Clients + Invoices from DB)
  → Returns ordered list with Pareto flag
```

### Flow 2 — Generate communication draft
```
Operator clicks "Generate draft"
  → POST /api/cases/{client_id}/communications/draft
  → Communications service builds prompt from case + config template
  → POST to OpenRouter → LLM returns draft text
  → Draft persisted to DB (status=draft)
  → Draft returned to frontend for operator review/edit
```

### Flow 3 — Send communication (human-in-the-loop)
```
Operator reviews/edits draft → clicks "Confirm and send"
  → POST /api/communications/{id}/send
  → Backend logs send event (timestamp, operator, model, prompt_version)
  → Status updated to "sent" — no real delivery (GR-SCOPE-002)
  → Audit record written
```

### Flow 4 — NL portfolio query
```
Executive types question
  → POST /api/scenarios/{id}/query  { "question": "..." }
  → NL service sends question + schema context to OpenRouter
  → LLM returns structured query plan + narrative
  → Backend executes query against DB
  → Returns data + narrative + source citation (RF-06.4)
```

### Flow 5 — Generate synthetic dataset
```
Demo Facilitator selects sector + parameters
  → POST /api/scenarios/generate  { sector, client_count, seed, ... }
  → Procedural layer generates quantitative data (NumPy/Faker/Pandas)
  → LLM enrichment call to OpenRouter for qualitative attributes
  → Full scenario persisted to DB
  → Scenario ID returned; frontend redirects to operations panel
```

---

## Deployment topology

```
          Vercel (Frontend)
               │
               │ HTTPS
               ▼
   Railway / Fly.io (FastAPI)
               │
               ├── TCP ──► PostgreSQL (managed, same platform)
               │
               └── HTTPS ──► OpenRouter
```
