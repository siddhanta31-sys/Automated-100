# Trend2Sketch Advanced Studio — Hardened Autonomous Build

This build fixes the overlapping/stuck-cycle behavior seen in Advanced Studio.

## Reliability protections added
- Cross-process single-cycle lock: Streamlit manual runs and the background worker cannot overlap.
- Orphan recovery on worker boot after deploy/restart.
- Stale-cycle recovery safety net.
- OpenAI request timeout and automatic retry/backoff.
- Web-research fallback when live web search fails.
- Concept generation no-hang guard: invalid selected-category responses are retried, and a usable partial pool continues instead of looping forever.
- Selected categories/lanes are explicitly constrained in the generation prompt and normalized safely.
- Concept scoring retries and continues with successful batches.
- Per-image rendering retries; one bad image cannot kill the whole batch.
- System Health shows WORKING / HEALTHY / ATTENTION REQUIRED.
- Manual Generate button is disabled while a cycle is already active.

All existing live controls remain: quality 75–100, exact 1–100 designs/cycle, autonomous ON/OFF, Diamond/South Indian lanes, product-category multiselect, custom categories, presets and calibration lab.

Recommended first run after deployment: Trial preset 75 / 10. Let one protected cycle complete before increasing quantity.
