#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

if [ -n "$1" ]; then
  # Scoped backend-only run — $1 is pytest path relative to backend/
  cd backend && .venv/bin/pytest "$1" -v
else
  # Full run: frontend + backend
  cd frontend && npm test -- --run
  cd ../backend && .venv/bin/pytest tests/ -v
fi
