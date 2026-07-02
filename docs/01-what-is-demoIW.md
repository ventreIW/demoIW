# What demoIW Is — and How It Works

> A plain-language guide for anyone: sales, new developers, or a prospect watching the demo.
> No prior knowledge assumed.

---

## In one sentence

**demoIW is a demonstration web app that shows how AI can make a company's debt-collection
(accounts receivable) smarter** — deciding *which unpaid invoices to chase first*, *how likely
each client is to pay*, and *what message to send them* — all on realistic, made-up data.

It is a **catalog / showcase asset** built by InterWare México to demonstrate our AI capability
to prospective clients. It is **not** wired to any real customer's data.

---

## The business problem it solves

Every company that sells on credit ends up with a pile of **unpaid invoices** (money it is owed).
A collections team has limited hours in the day and cannot call everyone. So they face three
hard questions every morning:

1. **Who is actually likely to pay** if we contact them? (Some clients always pay late but do
   pay; others will never pay.)
2. **Where is the money?** Chasing a big, collectible invoice is worth more than ten tiny ones.
3. **What do we say**, and through which channel, to actually get the payment?

Answering these by gut feel is slow and inconsistent. demoIW answers them with data + AI.

---

## What the system does (the demo story)

A facilitator running the demo goes through this flow:

```
   ┌──────────────┐   ┌─────────────┐   ┌──────────────┐   ┌───────────────┐
   │ 1. Generate  │──▶│ 2. Score    │──▶│ 3. Prioritise│──▶│ 4. Act        │
   │  a realistic │   │  each client│   │  by value ×  │   │  (AI-assisted │
   │  portfolio   │   │  (will they │   │  probability │   │  messages,    │
   │  of clients  │   │  pay?)      │   │  (Pareto)    │   │  human approves)│
   │  & invoices  │   │             │   │              │   │               │
   └──────────────┘   └─────────────┘   └──────────────┘   └───────────────┘
```

1. **Generate** — pick a business sector and a few parameters, click "Generar", and within
   seconds you have a full, realistic portfolio: companies, their invoices, and their payment
   histories.
2. **Score** — an ML model estimates each client's **collectability** (propensity to pay).
3. **Prioritise** — a Pareto engine orders the work by **value × probability**, so collectors
   spend their time where it pays off most.
4. **Act** — for the top-priority items, an AI drafts a suitable message (email / phone / WhatsApp,
   in the right tone). **A human always reviews before anything is "sent"** (human-in-the-loop).

Two dashboards close the loop:

- **Operations panel** — a collector's daily prioritised queue.
- **Executive panel** — a director's KPI dashboard, with a **natural-language query layer**
  ("How much is overdue in retail?") that turns plain questions into answers.

---

## The six modules

| # | Module | What it delivers |
|---|--------|------------------|
| 1 | **Synthetic dataset generator** | Realistic fake portfolios — statistical base + AI-written qualitative text |
| 2 | **Collectability evaluation engine** | ML propensity score: how likely each client is to pay |
| 3 | **Prioritisation engine** | Pareto ordering by value × probability |
| 4 | **Assisted communications generator** | AI-drafted collection messages, human-approved, via OpenRouter |
| 5 | **Operations panel** | Collector view: profile + daily priority queue |
| 6 | **Executive panel** | Director view: NL queries + KPI dashboard |

demoIW is being built module-by-module. Modules 1–2 (data + scoring foundations) come first
because everything else depends on having realistic, learnable data.

---

## How it works under the hood (technical overview)

**Shape of the system:** a web frontend talking to a Python backend over a REST API, with a
PostgreSQL database and an AI gateway for language tasks.

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js 15 · TypeScript · Tailwind · shadcn/ui (PWA) | Modern, installable web app; Spanish UI |
| Backend | Python 3.12 · FastAPI · Pydantic | Fast API layer with strong typing/validation |
| Database | PostgreSQL | Reliable relational store for scenarios, clients, invoices |
| AI gateway | **OpenRouter** (multi-model) | **Provider-agnostic** — never locked to one AI vendor |
| Synthetic data | Faker · NumPy · Pandas | Statistically realistic fake data |

**Architecture principle — hexagonal (ports & adapters).** The core business logic (domain
entities like `Client`, `Invoice`, `Payment`; value objects; use cases) is kept separate from the
outside world (database, HTTP, AI provider) by **ports** (interfaces) and **adapters**
(implementations). Concretely:

- **Domain** — pure business objects and rules (no database, no framework).
- **Ports** — interfaces such as `IScenarioRepository` (persistence) or `IDatasetPort`
  (data generation) that say *what* is needed, not *how*.
- **Adapters** — the *how*: a SQLAlchemy repository, a procedural data generator, an OpenRouter
  LLM client. Swapping PostgreSQL or the AI model means changing an adapter, not the core.

This keeps the demo **model-agnostic** (any AI model via OpenRouter) and **testable** (the core
runs against fakes/in-memory stores in tests).

---

## Why the data is synthetic

- **Confidentiality** — no real InterWare client information ever appears in the project.
- **Repeatability** — a facilitator can regenerate the *exact same* portfolio for a clean demo.
- **Control** — we can dial the scenario (sector, size) to show specific situations.

The interesting part is that the fake data is **not random noise**: it is engineered so that a
client's behaviour genuinely predicts their outcomes, which is what lets the scoring engine look
smart. The exact probability and statistics choices behind that are documented separately in
[`02-probability-and-statistics-decisions.md`](./02-probability-and-statistics-decisions.md).

---

## Where the project stands today

| Epic | Status |
|------|--------|
| **E1 — Project scaffolding & CI** | ✅ Done |
| **E2 — Data foundation** (domain schema, scenario API, CSV upload, selector UI) | ✅ Done |
| **E3 — Synthetic dataset generator** | 🔄 In progress — the **procedural generation layer** (s3.1) is built |
| E4 — Collectability scoring · E5 — Communications · E6 — Executive panel | ⬜ Upcoming |

**Timeline:** May 4 – August 14, 2026 (14 weeks). Built under the **RaiSE** methodology
(disciplined story lifecycle: design → plan → TDD implementation → review → close).

---

## The 30-second pitch

> "We generate a realistic book of overdue invoices, let AI score who's worth chasing and rank
> them by expected recovery, draft the outreach for a human to approve, and show it all on
> collector and executive dashboards — model-agnostic, on synthetic data, ready to demo in
> seconds."
