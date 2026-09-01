# Trend2Sketch Foolproof Design OS

This build focuses on useful design work and recovery rather than raw image volume.

## What changed
- Automatic visual Design DNA analysis for every owner-approved uploaded reference.
- Separate Design DNA profiles (South Indian Bridal, Lightweight South Indian, Diamond Everyday, etc.).
- Uploaded image analysis extracts silhouette, motif language, stone hierarchy, setting language, weight philosophy, manufacturability and abstract generation directives.
- Excellent / Usable / Reject feedback remains part of Deep research; rejected designs disappear from the visible library.
- Timeout-resilient small-batch Deep exploration.
- Heartbeat-based stale-cycle recovery, so a long healthy cycle is not incorrectly killed just because it has been running for a long time.
- Stage checkpoints for research, concepts, scoring, shortlist and render progress.
- Supervisor auto-restarts the worker with exponential backoff after a process crash.
- Existing single-cycle lock, persistent SQLite/WAL, budget/resource guards, retry logic and persistent controls are retained.

## Important reliability note
No cloud app can be guaranteed to never fail because Render, OpenAI, networking or disk services can fail. This build is designed to fail safely, retain progress, recover automatically and avoid duplicate cycles.

## Recommended first run
Deep mode, 10 final designs, threshold 75. Upload 10-20 strong reference designs into one clear Design DNA profile before judging output quality. Rate every result.
