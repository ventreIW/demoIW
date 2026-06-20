#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
cd frontend && npm test -- --run
cd ../backend && .venv/bin/pytest tests/ -v
