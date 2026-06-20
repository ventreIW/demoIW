#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
cd frontend && npm run typecheck
cd ../backend && .venv/bin/mypy app/
