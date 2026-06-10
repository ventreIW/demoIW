# Module: Ports (Interfaces)

Traces to: `governance/guardrails.md § GR-ARCH-004`

Ports are abstract interfaces defined in the application/domain layer. They describe *what* the application needs from the outside world without specifying *how* it is provided. Adapters implement ports.

---

## Location (backend)

```
backend/
  app/
    ports/
      repositories.py   # data persistence interfaces
      llm_port.py       # LLM gateway interface
      dataset_port.py   # synthetic data generation interface
      analytics_port.py # structured query execution interface
      scoring_port.py   # ML model inference interface
```

---

## Port definitions

### IScenarioRepository
```python
class IScenarioRepository(ABC):
    def save(self, scenario: Scenario) -> None: ...
    def get_by_id(self, scenario_id: UUID) -> Scenario | None: ...
    def get_active(self) -> Scenario | None: ...
    def list_all(self) -> list[Scenario]: ...
    def set_active(self, scenario_id: UUID) -> None: ...
```

### IClientRepository
```python
class IClientRepository(ABC):
    def save_many(self, clients: list[Client]) -> None: ...
    def get_by_id(self, client_id: UUID) -> Client | None: ...
    def list_by_scenario(self, scenario_id: UUID) -> list[Client]: ...
    def get_with_invoices(self, client_id: UUID) -> ClientDetail | None: ...
```

### IScoreRepository
```python
class IScoreRepository(ABC):
    def save(self, score: Score) -> None: ...
    def save_many(self, scores: list[Score]) -> None: ...
    def get_latest(self, client_id: UUID, scenario_id: UUID) -> Score | None: ...
    def list_by_scenario(self, scenario_id: UUID) -> list[Score]: ...
```

### ICommunicationRepository
```python
class ICommunicationRepository(ABC):
    def save(self, communication: Communication) -> None: ...
    def get_by_id(self, communication_id: UUID) -> Communication | None: ...
    def list_by_client(self, client_id: UUID) -> list[Communication]: ...
    def update_status(self, communication_id: UUID, status: CommunicationStatus, final_content: str | None) -> None: ...
```

### IContactResultRepository
```python
class IContactResultRepository(ABC):
    def save(self, result: ContactResult) -> None: ...
    def list_by_client(self, client_id: UUID) -> list[ContactResult]: ...
```

### ILLMPort
```python
class ILLMPort(ABC):
    def generate(self, prompt: str, model: str, max_tokens: int) -> str: ...
    def query(self, system_prompt: str, user_message: str, model: str) -> str: ...
```
The model parameter is always read from config (GR-AI-002). Adapters must never hardcode a model name.

### IDatasetPort
```python
class IDatasetPort(ABC):
    def generate_procedural(self, params: GenerationParams) -> RawDataset: ...
    def load_from_csv(self, file_path: str) -> RawDataset: ...
```

### IAnalyticsPort
```python
class IAnalyticsPort(ABC):
    def execute_query(self, query_plan: StructuredQueryPlan) -> QueryResult: ...
    def get_portfolio_kpis(self, scenario_id: UUID) -> PortfolioKPIs: ...
```

### IScoringModel
```python
class IScoringModel(ABC):
    def predict(self, features: list[ClientFeatures]) -> list[ScorePrediction]: ...
    def model_version(self) -> str: ...
```

---

## Dependency direction

```
Application layer
  ──uses──► Ports (interfaces)
              ◄──implements── Adapters (infrastructure layer)
```

The application layer imports only from `app.ports` and `app.domain`. It never imports from `app.adapters` or `app.infrastructure`.
