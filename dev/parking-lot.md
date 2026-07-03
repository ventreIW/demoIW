# Parking Lot

Ideas not ready for the backlog. No commitment, no timeline. Review at each epic close.

Items that get scoped move to `governance/backlog.md`.

---

| Date added | Idea | Why parked |
|---|---|---|
| 2026-06-10 | Simulation mode — replay scenario over time (show recovery progression day by day) | High demo value, high complexity. Revisit after core modules ship. |
| 2026-06-10 | Webhook integration to external email/WhatsApp services | Out of demonstrative scope per restrictions. No real sends in demo. |
| 2026-06-10 | Multi-tenant / multi-organization support | Demonstrative scope is single-org. Future product direction only. |
| 2026-06-10 | Custom ML model training UI (upload training data, retrain in-browser) | Complex, not needed for demo conviction. |
| 2026-07-02 | RaiSE framework: `rai session start` should sync/verify backend venv against `requirements.txt` | Found in s3.1 — venv was missing `python-multipart` (committed in s2.5) and had no `pip`; only surfaced on a test import failure. |
| 2026-07-02 | RaiSE framework: fix orphaned-test check diff range in `rai-story-implement` | Uses reversed `git diff HEAD...$base`, producing false positives (flagged s3.1's own new test). Correct form: `git diff --name-only main...HEAD`. |
