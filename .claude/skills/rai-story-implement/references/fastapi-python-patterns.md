# FastAPI and Python Implementation Patterns

## Stale __pycache__ Issues

### Problem
After modifying Python code (especially FastAPI routers), encountering confusing errors like:
- `TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'`
- Import errors that don't match the actual code
- Methods appearing to be missing or changed

### Cause
Stale Python bytecode cache (__pycache__ directories) retaining old compiled code that doesn't match the updated source files.

### Solution
Clear __pycache__ directories after modifying Python code:
```bash
# Clear __pycache__ in the entire backend
find backend -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Or clear for specific modules
find backend/app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
```

### Prevention
- Make clearing __pycache__ part of your development workflow after code changes
- Consider adding a script or alias for this operation
- In CI/CD pipelines, ensure clean checkouts to avoid this issue entirely

## FastAPI Route Ordering

### Problem
Specific routes like `/active` or `/upload-csv` returning 404 errors, even though they are defined in the code.

### Cause
In FastAPI, route matching is order-dependent. A route with a path parameter like `/{scenario_id}` defined BEFORE a specific route like `/active` will capture `/active` as a value for the `scenario_id` parameter, leading to unexpected behavior or 404 errors if the parameter validation fails.

### Solution
Always define specific routes BEFORE parameterized routes:
```python
# CORRECT ORDER - specific routes first
@app.get("/active")
async def get_active(): ...

@app.get("/upload-csv")
async def upload_csv(): ...

@app.get("/{scenario_id}")  # Parameterized route LAST
async def get_scenario(scenario_id: str): ...
```

### Incorrect Order (causes issues):
```python
# WRONG ORDER - parameterized route first
@app.get("/{scenario_id}")  # This will capture "/active" and "/upload-csv"
async def get_scenario(scenario_id: str): ...

@app.get("/active")  # Never reached due to above route
async def get_active(): ...

@app.get("/upload-csv")  # Never reached due to above route
async def upload_csv(): ...
```

## PostgreSQL vs SQLite in WSL Development

### Problem
PostgreSQL database connection failures in WSL environment when trying to run the application or tests.

### Cause
PostgreSQL server not installed or not running in the WSL distribution, or connection configuration pointing to a non-existent PostgreSQL instance.

### Solution
For development and testing in WSL:
1. Use SQLite with aiosqlite for integration tests (already configured in conftest.py):
   ```python
   TEST_DATABASE_URL = "sqlite+aiosqlite:///"
   ```
2. This provides a fully functional, zero-setup database for testing
3. Reserve PostgreSQL testing for CI/CD environments or dedicated development setups

### Verification
Tests using `sqlite+aiosqlite:///` will:
- Run quickly (no external dependencies)
- Provide full SQLAlchemy functionality
- Be isolated between test runs
- Catch the same application logic bugs as PostgreSQL

## CSV Upload Endpoint Implementation

### Key Implementation Details
When implementing a FastAPI CSV upload endpoint with validation:

1. **Dependencies**: Requires `python-multipart` package
   ```toml
   # requirements.txt
   python-multipart==0.0.32
   ```

2. **Endpoint Signature**:
   ```python
   @router.post("/upload-csv", response_model=ScenarioSummary, status_code=201)
   async def upload_csv(
       file: UploadFile,
       repo: IScenarioRepository = Depends(get_scenario_repo)
   ) -> ScenarioSummary:
   ```

3. **Validation Steps**:
   - Check for empty file
   - Validate UTF-8 encoding
   - Parse CSV with `csv.DictReader`
   - Validate required columns
   - Ensure data rows exist
   - Derive scenario name from filename

4. **Error Handling**:
   - Return 422 status for validation errors
   - Use FastAPI's standard error format: `detail: [{"msg": "error message"}]`
   - Provide specific, actionable error messages

5. **Database Operations**:
   - Use repository pattern for transactional integrity
   - Create all related entities (Scenario, Client, Invoice) in a single transaction
   - Commit only after all entities are successfully added

### Testing Approach
Write integration tests for:
- Happy path: valid CSV returns 201 with correct data
- Missing columns: returns 422 with specific error message
- Empty file: returns 422
- Malformed CSV: returns 422 with parse error

These tests provide confidence in the implementation without requiring manual verification.

## Adding New Settings via Pydantic Settings

When adding new configuration settings to a FastAPI application that uses Pydantic Settings (BaseSettings), follow these steps:

1. **Add fields to the Settings class** in `app/config.py`:
   - Add the new fields with appropriate types.
   - Provide default values if the settings are optional (e.g., empty strings) to avoid startup errors when the environment variables are not set.
   - Example:
     ```python
     OPENROUTER_API_KEY: str = ""
     OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
     MODEL_DATA_ENRICHMENT: str = ""
     MODEL_COMMUNICATIONS: str = ""
     MODEL_NL_QUERY: str = ""
     ```

2. **Update the `.env.example` file** to include the new variables with placeholder values or comments:
   - This helps developers know which environment variables are expected.
   - Example:
     ```ini
     # OpenRouter
     OPENROUTER_API_KEY=***     OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
     MODEL_DATA_ENRICHMENT=
     MODEL_COMMUNICATIONS=
     MODEL_NL_QUERY=
     ```

3. **Update the application code** to use the new settings via the `settings` singleton:
   - Import the settings from `app.config`: `from app.config import settings`
   - Access the values as `settings.OPENROUTER_API_KEY`, etc.

4. **Consider security**: If the setting is a secret (like an API key), ensure it is marked as such in your secrets management and never committed to the repository. The `.env.example` should have empty or placeholder values.

5. **Run type checking**: After adding the fields, run `mypy` to ensure there are no type errors.

This pattern ensures that the application remains configurable via environment variables and that the configuration is centralized and type-safe.