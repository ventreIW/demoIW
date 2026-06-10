# Module: Application Layer

Traces to: `governance/prd.md § RF-01–RF-07`, `governance/guardrails.md § GR-ARCH-004`

The application layer orchestrates use cases. It calls domain objects and invokes ports — never adapters directly. No HTTP, no SQL.

---

## Location (backend)

```
backend/
  app/
    application/
      use_cases/
        generate_dataset.py
        score_portfolio.py
        prioritize_cases.py
        generate_communication_draft.py
        send_communication.py
        record_contact_result.py
        get_portfolio_kpis.py
        run_nl_query.py
        manage_scenario.py
      services/
        scoring_service.py       # wraps ML model inference
        prioritization_service.py
        prompt_builder.py        # builds LLM prompts from templates + case data
```

---

## Use case catalog

### GenerateDataset
- **Input:** `GenerateDatasetCommand(sector, client_count, invoice_volume, overdue_rate_dist, seed)`
- **Steps:** Run procedural generator → request qualitative enrichment via `ILLMPort` → persist via `IScenarioRepository`
- **Output:** `ScenarioSummary`
- **Traces to:** RF-01

### ScorePortfolio
- **Input:** `ScorePortfolioCommand(scenario_id)`
- **Steps:** Load clients from `IClientRepository` → run feature engineering → call `IScoringModel.predict()` → persist scores via `IScoreRepository`
- **Output:** list of `ScoreSummary`
- **Traces to:** RF-02

### PrioritizeCases
- **Input:** `PrioritizeCasesQuery(scenario_id, filters?)`
- **Steps:** Load clients + scores → compute PriorityValue per client → sort desc → apply Pareto filter → return ordered list
- **Output:** list of `PriorityEntry`
- **Traces to:** RF-03

### GenerateCommunicationDraft
- **Input:** `GenerateDraftCommand(client_id, channel, tone, operator_id)`
- **Steps:** Load case detail from `IClientRepository` → build prompt via `PromptBuilder` → call `ILLMPort.generate()` → persist draft via `ICommunicationRepository`
- **Output:** `CommunicationDraft`
- **Traces to:** RF-04.1, RF-04.2, RF-04.5, RF-04.6

### SendCommunication
- **Input:** `SendCommunicationCommand(communication_id, final_content, operator_id)`
- **Steps:** Load draft → validate operator_id present → update `final_content` → set `status = SENT` → write audit record → persist
- **Output:** `CommunicationConfirmation`
- **Traces to:** RF-04.4, NFR-06, GR-AI-003

### RecordContactResult
- **Input:** `RecordContactResultCommand(client_id, result, notes, operator_id, communication_id?)`
- **Steps:** Persist `ContactResult` → emit domain event → trigger `ScorePortfolio` for affected client
- **Output:** `ContactResultSummary`
- **Traces to:** RF-05.3, RF-02.5

### GetPortfolioKPIs
- **Input:** `GetPortfolioKPIsQuery(scenario_id)`
- **Steps:** Aggregate from `IClientRepository` + `IScoreRepository` → compute KPI bundle
- **Output:** `PortfolioKPIs`
- **Traces to:** RF-06.1, RF-06.2

### RunNLQuery
- **Input:** `RunNLQueryCommand(scenario_id, question)`
- **Steps:** Build context (schema + active scenario metadata) → call `ILLMPort.query()` → parse structured query plan from LLM response → execute query via `IAnalyticsPort` → return data + narrative + source citation
- **Output:** `NLQueryResult`
- **Traces to:** RF-06.3, RF-06.4

### ManageScenario
- **Input:** `ActivateScenarioCommand(scenario_id)` / `UploadCSVCommand(file)` / `ListScenariosQuery()`
- **Traces to:** RF-07
