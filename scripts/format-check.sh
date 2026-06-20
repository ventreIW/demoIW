#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
cd frontend && npx prettier --check .
cd ../backend && .venv/bin/ruff format --check .
