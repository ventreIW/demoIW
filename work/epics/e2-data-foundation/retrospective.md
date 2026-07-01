# Epic Retrospective: E2 Data Foundation

**Completed:** 2026-07-01
**Duration:** 13 days (started 2026-06-18)
**Stories:** 5 stories delivered

---

## Summary
E2 estableció la base de datos del dominio: ORM models para 7 entidades, Pydantic models separados, mappers bidireccionales, migraciones Alembic, API REST completa para escenarios (list, create, get, activate, get active, upload-csv), repositorio SQLAlchemy con patrón de repositorio, tests de integración que cubren todos los endpoints, y UI de selector de escenarios con file picker para carga CSV. El épico habilita que los facilitadores creen escenarios vía CSV upload y activen escenarios para iniciar la simulación.

## Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Stories Delivered | 5 | s2.1 → s2.5 |
| Story Points | 16 SP | s2.1: 5, s2.2: 4, s2.3: 3, s2.4: 2, s2.5: 2 |
| Tests Added | 39 | backend tests (API, entities, mappers, health, csv upload) |
| Average Velocity | 1.23 SP/día | 16 SP / 13 días |
| Calendar Days | 13 | desde inception hasta cierre |

### Story Breakdown

| Story | Size | SP | Velocity | Key Learning |
|-------|:----:|:--:|:--------:|--------------|
| s2.1 | L | 5 | 2.0x | ORM ↔ Pydantic mappers son esenciales para mantener separación de dominio/persistencia |
| s2.2 | M | 4 | 3.0x | Patrón de repositorio con transacciones async permite operaciones atómicas limpias |
| s2.3 | M | 3 | 2.5x | Route guards y cookie-based state son efectivos para protección de rutas en Next.js |
| s2.4 | S | 2 | 4.0x | Componentes de archivo en Next.js deben ser client-only; usar wrapper para router |
| s2.5 | S | 2 | 6.0x | CSV parsing con stdlib + patrón de repositorio compuesto evita servicios anémicos |

## What Went Well

- **TDD rigoroso**: Cada story siguió RED-GREEN-REFACTOR, incluyendo tests de integración antes de la implementación.
- **Separación de preocupaciones clara**: ORM models (persistence), Pydantic models (domain), mappers (translation layer), repositorios (ports).
- **Consistencia de contrato**: El frontend de s2.4 y el backend de s2.5 coincidieron exactamente en el formato de request/response (422 con `detail: [{msg}]`, 200/201 con `ScenarioSummary`).
- **Cobertura de testing**: 39 pruebas de integración que cubren happy paths, edge cases y errores de validación.
- **Migraciones automáticas**: Alembic crea tablas, índice único y datos semilla sin intervención manual.

## What Could Be Improved

- **Documentación de CSV**: El formato de columnas requeridas (`client_name`, `amount`, `due_date`, `invoice_id`) debería estar en un `README.md` o similar para referencia rápida del usuario.
- **Manejo de errores de CSV**: Los mensajes de error 422 podrían incluir el número de línea fallida para facilitar corrección por parte del usuario.
- **Velocidad de pruebas en WSL**: Los tests de integración son rápidos (~0.5s) pero en un entorno real con PostgreSQL podrían ser más lentos; considerar pruebas unitarias de repositorio con SQLite en CI.
- **Separación de responsabilidades en el repositorio**: El método `create_from_csv` podría delegar a servicios de dominio para mantener el repositorio únicamente como puerto de persistencia.

## Patterns Discovered

| ID | Pattern | Context |
|----|---------|---------|
| PAT-N-1 | SQLite commit vs flush | En pruebas de integración con `sqlite+aiosqlite://`, usar `await session.commit()` para persistir datos visibles en consultas subsiguientes; `flush()` solo asigna IDs pero no los hace visibles a otras transacciones. |
| PAT-N-2 | FastAPI route ordering | Rutas con parámetros de path (`/{scenario_id}`) deben definirse *después* de rutas específicas (`/active`, `/upload-csv`) para evitar que `/active` coincida con el parámetro y devuelva 404. |
| PAT-N-3 | Repositorio compuesto | Métodos como `create_from_csv` que crean múltiples entidades relacionadas (Scenario + Client + Invoice) deben residir en el repositorio para mantener la atomicidad transaccional y evitar servicios anémicos. |
| PAT-N-4 | Backend agnóstico de frontend | El endpoint `upload-csv` no asume nada sobre el cliente más allá del contrato HTTP; el mismo endpoint sirve a cualquier cliente (curl, Postman, frontend React). |

## Process Insights

- **Historia dividida correctamente**: Dividir s2.4 en frontend (Renata) y backend (Nano) funcionó porque el contrato fue acordado de antemano y ambos pudieron trabajar en paralelo.
- **Retrospectivas tempranas escriben historia**: Escribir la retrospectiva de cada story inmediatamente después del cierre evitó pérdida de aprendizaje y permitió acumular patrones como PAT-N-1 y PAT-N-2.
- **Orden de rutas importa en FastAPI**: Un patrón sutil que se descubrió en s2.2 y se aplicó en s2.5 evitó horas de depuración.
- **Los pruebas de integración son el verdadero contrato**: Pasar las 39 pruebas dio más confianza que cualquier revisión de código o inspección manual.

## Artifacts

- **Scope:** `work/epics/e2-data-foundation/scope.md`
- **Stories:** `work/epics/e2-data-foundation/stories/` (s2.1-* → s2.5-*)
- **ADRs:** ADR-002 (active scenario constraint) en `governance/adr/ADR-002-active-scenario-constraint.md`
- **Tests:** 39 nuevos tests en `backend/tests/`

## Release Impact

**Release:** REL-0.2.0 (E2 Data Foundation)
**Epic progress:** 1/1 epics completados para esta release

> Esta release establece la base sobre la cual E3 (Synthetic Dataset Generator) podrá generar escenarios realistas con datos de clientes y facturas.

## Next Steps

- [E3] Generador de conjuntos de datos sintéticos poblará los escenarios con datos de clientes y facturas realistas.
- [E4] Motor de scoring evaluará el rendimiento de los clientes contra sus facturas.
- [E5/L1] Paneles de operaciones y ejecutivo mostrarán métricas derivadas de los datos generados.