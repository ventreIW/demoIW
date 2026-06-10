# System Context (C1)

Traces to: `governance/vision.md`, `governance/prd.md § RF-01–RF-07`

---

## System boundary

**demoIW** is a web application that provides intelligent accounts receivable management over fully synthetic datasets. It operates as a standalone demo asset — no integrations with real ERP, CRM, or email services are required or permitted (GR-SCOPE-002).

---

## Actors

| Actor | Profile | Interaction |
|---|---|---|
| Collections Operator | P-01 — Staff-level, non-technical | Works the daily priority queue; reviews and confirms communication drafts |
| Executive / Finance Director | P-02 — Decision-maker | Monitors portfolio KPIs; issues natural-language queries |
| Demo Facilitator | P-03 — InterWare consultant | Loads sector scenarios; navigates both profiles during a live demo |

All actors interact through a browser or installed PWA (NFR-04).

---

## External systems

| System | Role | Protocol |
|---|---|---|
| **OpenRouter** | AI gateway — routes LLM calls to best-fit models; provides OpenAI-compatible API | HTTPS / OpenAI-compatible REST |
| **PostgreSQL** | Persistent store for scenarios, clients, invoices, payments, scores, and communications | TCP — internal to backend only |

### What OpenRouter is used for

| Use case | Requirement |
|---|---|
| Qualitative synthetic data enrichment | RF-01.3 |
| Communication draft generation | RF-04.2 |
| Natural language portfolio query | RF-06.3 |

No other AI provider is accessed directly at any point (GR-AI-001).

---

## Context diagram (text)

```
┌────────────────────────────────────────────────────────────────────┐
│                            demoIW                                  │
│                                                                    │
│   ┌──────────────┐    REST/JSON    ┌──────────────────────────┐   │
│   │  Next.js PWA │◄──────────────►│   FastAPI Backend         │   │
│   │  (Frontend)  │                │   (Business logic,        │   │
│   └──────────────┘                │    scoring, AI orchestr.) │   │
│                                   └────────────┬─────────────┘   │
│                                                │                   │
│                                    ┌───────────┴──────────┐       │
│                                    │     PostgreSQL        │       │
│                                    └──────────────────────┘       │
└─────────────────────────────────────┬──────────────────────────────┘
                                      │ HTTPS
                                ┌─────▼──────┐
                                │ OpenRouter │
                                └────────────┘

  Actors (browser / PWA):
    [Collections Operator] ──► [Frontend]
    [Executive]            ──► [Frontend]
    [Demo Facilitator]     ──► [Frontend]
```

---

## Out of scope (by GR-SCOPE-002)

- Real email / WhatsApp send
- ERP or CRM read/write
- Real-time bank feed
- User authentication beyond a simple profile switcher (B-17 is under consideration)
