#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
cd frontend && npm run lint
cd ../backend && .venv/bin/ruff check .
