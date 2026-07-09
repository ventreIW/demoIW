# Known Issue 001: Starlette/FastAPI Version Mismatch

**Date discovered:** 2026-07-07
**Status:** Workaround documented, not permanently fixed
**Affects:** backend/ (any environment reinstalling dependencies from requirements.txt)

## Symptom

Tests fail with:

TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'

This surfaces when pytest tries to load conftest.py, which imports app.main,
which imports routers that instantiate APIRouter.

## Root Cause

backend/requirements.txt pins fastapi==0.115.6 but never pins starlette,
which FastAPI depends on internally. FastAPI 0.115.6 requires
starlette>=0.40.0,<0.42.0. Without an explicit pin, a fresh install can pull
a much newer, incompatible Starlette version (observed: 1.3.1) directly from
PyPI, since nothing in the project constrains it.

## Fix (not permanent — repeats on fresh installs)

uv pip install --force-reinstall "fastapi==0.115.6"

This forces pip/uv to reinstall Starlette within FastAPI's compatible range.

This fix does not persist. It only affects the current virtual environment.
If the .venv is rebuilt (uv sync, fresh clone + install, CI environment,
etc.), the mismatch can reappear.

## Recommended Permanent Fix (not yet applied)

Per FastAPI's own guidance, Starlette should generally not be pinned manually —
letting FastAPI resolve its own dependency is preferred. The actual fix should
be at the dependency resolution level: ensure requirements.txt (or a lockfile,
if the team adopts one) captures the exact resolved Starlette version, so a
fresh install reproduces the same environment instead of pulling latest.

## How to Diagnose This Issue Again

uv pip show starlette | grep Version

If the version is outside 0.40.x-0.41.x, this is the cause.
