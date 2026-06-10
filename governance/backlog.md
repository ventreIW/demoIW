# Backlog

Raw idea pool — items not yet assigned to an epic. Prioritized top-to-bottom within each section.

Items move from here → epic `brief.md` when an epic is started via `/rai-epic-start`.  
Ideas not ready for the backlog go to `dev/parking-lot.md`.

---

## Ready (scoped and prioritized)

| ID | Title | Size | RF trace | Notes |
|---|---|---|---|---|
| B-01 | Project scaffolding & CI baseline | XS | — | Monorepo layout, Next.js 15 init, FastAPI init, PostgreSQL connection, GitHub Actions pipeline |
| B-02 | Data model & database schema | S | RF-01, RF-02, RF-05 | Entities: Client, Invoice, Payment, Communication, Score. Migrations with Alembic. |
| B-03 | Synthetic dataset generator — procedural layer | M | RF-01 | NumPy distributions, Faker identities, Pandas assembly. Seed-based reproducibility. |
| B-04 | Synthetic dataset generator — LLM enrichment layer | S | RF-01.3 | OpenRouter integration, qualitative attribute enrichment, prompt template v1 |
| B-05 | Collectability scoring engine | M | RF-02 | Feature engineering, model training on synthetic data, score + explanation output |
| B-06 | Prioritization engine | S | RF-03 | Priority value formula, Pareto filter, sort/filter API |
| B-07 | Scenario management API + UI | S | RF-07 | Pre-loaded scenarios, CSV upload, active scenario indicator |
| B-08 | Operations panel — case list view | S | RF-05.1–RF-05.4 | Priority queue display, filters, status update |
| B-09 | Operations panel — case detail view | S | RF-05.2–RF-05.5 | Full case profile, invoice list, payment history, communications log |
| B-10 | Communications generator — backend | S | RF-04 | OpenRouter call, prompt template, draft persistence, audit log |
| B-11 | Communications generator — frontend flow | S | RF-04.3–RF-04.5 | Editable draft UI, channel/tone selector, confirmation flow |
| B-12 | Executive panel — KPI dashboard | M | RF-06.1–RF-06.2 | Portfolio metrics, segmentation charts |
| B-13 | Executive panel — NL query layer | M | RF-06.3–RF-06.4 | Query input, SQL translation, visualization, narrative response |
| B-14 | PWA configuration | XS | NFR-04 | next-pwa config, manifest, service worker |
| B-15 | i18n setup (ES/EN) | S | NFR-03 | next-intl or equivalent, ES default, EN alternative |
| B-16 | End-to-end demo flow validation | S | NFR-01 | Full demo path smoke test, <10 min flow verification |

---

## Under consideration (needs scoping)

| ID | Title | Notes |
|---|---|---|
| B-17 | Role-based access (operator vs. executive) | Simple session-based auth, two roles. Decide if needed for demo or just profile switcher. |
| B-18 | Real-time score recalculation on contact result | Trigger rescoring after RF-02.5; may be out of scope for demo timeline. |
| B-19 | Export portfolio report as PDF | Nice-to-have for demo handoff. Assess after core modules. |
| B-20 | Simulation mode (replay scenario progression over time) | High demo value but high complexity. Park for now. |

---

## Sizing reference

| Size | Typical story count | Rough effort |
|---|---|---|
| XS | 1–2 stories | < 1 day |
| S | 2–4 stories | 1–3 days |
| M | 4–7 stories | 3–7 days |
| L | 8+ stories | > 1 week |
