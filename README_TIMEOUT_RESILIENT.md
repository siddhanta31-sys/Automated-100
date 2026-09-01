# Timeout-Resilient Deep Mode

This build fixes repeated `APITimeoutError` during Deep concept discovery.

Changes:
- Deep concept batches reduced from 40 concepts to 8.
- Up to 3 concept workers run small jobs concurrently.
- Failed batches automatically split into smaller sub-batches.
- Successful sub-batches are retained as checkpoints instead of losing the whole batch.
- API request timeout default increased from 120s to 180s.
- Concept calls use two attempts before splitting, avoiding very long retry stalls.
- Deep mode still targets the same full concept pool; only the request granularity changed.

Recommended first test: Deep, 10 rendered designs, quality threshold 75.
