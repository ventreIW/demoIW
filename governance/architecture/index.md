# Architecture Index

Traces to: `governance/vision.md`, `governance/prd.md`

This directory holds the living architectural specification for demoIW. All epic and story designs must anchor to these documents. Significant deviations require an ADR in `dev/decisions/`.

---

## Documents

| Document | Scope | Description |
|---|---|---|
| [system-context.md](system-context.md) | C1 — Context | Actors, the system boundary, and external dependencies |
| [system-design.md](system-design.md) | C2 — Containers | Runtime containers, their responsibilities, and communication |
| [domain-model.md](domain-model.md) | Domain | Core entities, relationships, and invariants |
| [modules/domain.md](modules/domain.md) | Backend | Domain layer: entities, value objects, domain rules |
| [modules/application.md](modules/application.md) | Backend | Application layer: use cases and orchestration |
| [modules/ports.md](modules/ports.md) | Backend | Port interfaces (hexagonal boundary) |
| [modules/adapters.md](modules/adapters.md) | Backend | Adapter implementations (DB, OpenRouter, CSV) |
| [modules/infrastructure.md](modules/infrastructure.md) | Backend | Infrastructure concerns: migrations, config, logging |
| [modules/cross_cutting.md](modules/cross_cutting.md) | Backend | Cross-cutting concerns: error handling, audit log, prompt templates |

---

## Governing constraints

- **GR-ARCH-001:** Frontend and backend are decoupled; only REST API communication.
- **GR-ARCH-003:** No business logic in the frontend.
- **GR-ARCH-004:** Backend follows hexagonal architecture (ports and adapters).
- **GR-AI-001:** All LLM calls route through OpenRouter — never directly to a vendor API.
- **GR-AI-002:** Model name comes from configuration, never hardcoded.

---

## Decision log

ADRs are in `dev/decisions/`. Index maintained there as decisions accumulate.
