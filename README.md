# demoIW

Aplicación web para la gestión integral de ventas organizacionales — InterWare México S.A. de C.V.

## Local dev setup

### Prerequisites

- Node.js 20+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- PostgreSQL 16+ (required for backend stories s1.3+)

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
npm run typecheck  # TypeScript check
npm run lint       # ESLint
npm test           # Vitest (watch mode)
npm test -- --run  # Vitest (single run)
```

### Backend

```bash
cd backend
uv venv .venv --python 3.12
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate       # Windows

uv pip install -r requirements-dev.txt

uvicorn app.main:app --reload  # http://localhost:8000 (available from s1.3)
ruff check .                   # Linter
mypy app/                      # Type check
pytest tests/ -v               # Tests
```

### Environment

Copy `.env.example` to `.env` and fill in your values before starting the backend (required from s1.3).

## CI

GitHub Actions runs on every PR to `main`:
- **frontend**: typecheck → lint → test
- **backend**: ruff → mypy → pytest
