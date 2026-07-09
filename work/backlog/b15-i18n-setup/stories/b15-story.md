---
story_id: "B-15"
epic_ref: null
size: "S"
type: "code"
status: "draft"
---

# Story: i18n Setup (next-intl)

## User Story
As a user of the demoIW application,
I want the UI to display in my preferred language (English or Spanish),
so that I can navigate and use the application in a language I understand.

## Acceptance Criteria

### Scenario: Spanish locale renders all UI in Spanish (default)
```gherkin
Given the user's browser preference is Spanish (or no preference)
When they visit any page of the application
Then all UI strings render in Spanish
And the HTML lang attribute is "es"
And the page metadata (title, description) is in Spanish
```

### Scenario: English locale renders all UI in English
```gherkin
Given the user's browser preference is English
Or they navigate to /en/*
When they visit any page of the application
Then all UI strings render in English
And the HTML lang attribute is "en"
And the page metadata is in English
```

### Scenario: Missing translation key falls back to key name
```gherkin
Given a translation key does not exist in the active locale's message file
When that key is rendered
Then the key name itself is displayed (next-intl default behavior — no silent failures)
```

### Scenario: Sidebar navigation links are translated
```gherkin
Given the active locale
When the sidebar is rendered
Then all navigation link labels are translated
```

### Scenario: Status badges and sector labels are translated in scenario cards
```gherkin
Given the active locale
When a scenario card is rendered
Then the status badge text and sector label are translated
```

## Examples (Specification by Example)

| Component | String (Spanish) | Translation Key |
|-----------|-----------------|-----------------|
| Sidebar | "Operaciones" | `sidebar.operations` |
| Sidebar | "Ejecutivo" | `sidebar.executive` |
| Sidebar | "Escenarios" | `sidebar.scenarios` |
| ScenarioCard | "Activo" | `scenario.status.active` |
| ScenarioCard | "Sin datos" | `scenario.status.noData` |
| ScenarioCard | "Con datos" | `scenario.status.withData` |
| ScenarioCard | "X clientes" | `scenario.clientCount` (ICU: `{count} clientes`) |
| ScenarioCard | "Seleccionar" | `scenario.actions.select` |
| ScenarioCard | "Activando..." | `scenario.actions.activating` |
| CsvUpload | "Subir CSV" | `csv.uploadButton` |
| CsvUpload | "Subir" | `csv.upload` |
| CsvUpload | "Subiendo..." | `csv.uploading` |
| CsvUpload | "Seleccionar archivo CSV" | `csv.selectFile` |
| CsvUpload | "Cancelar seleccion" | `csv.cancelSelection` |
| CsvUpload | "Error al subir el archivo." | `csv.errorUpload` |
| CsvUpload | "Escenario \"{name}\" creado correctamente." | `csv.successCreated` |
| layout.tsx | "demoIW" | `app.title` |
| layout.tsx | "Industrial wastewater treatment..." | `app.description` |
| ScenarioCard | Sector names (manufacturing, retail, professional_services) | `sectors.manufacturing`, etc. |

## Notes

- Use `next-intl` — the de facto standard for Next.js App Router i18n
- Next.js 15.3.3, React 19 — App Router with Server Components
- Default locale: `es` (Spanish) as established by the existing codebase
- Supported locale: `en` (English)
- Locale detection: `accept-language` header via next-intl middleware
- All UI strings are currently in `es` (the default) — `en.json` will be created with English equivalents
- ICU message format for pluralization (`{count} clientes` → `{count, plural, =1 {1 cliente} other {# clientes}}`)
- No locale prefix for default locale (`es` renders at `/`, `en` at `/en`)
- No i18n needed for backend (FastAPI) — frontend-only change