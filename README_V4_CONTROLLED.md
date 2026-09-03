# Trend2Sketch DesignOS V4 — Controlled Research Edition

This release replaces the V3 volume-first workflow with a manual, research-first
discovery workflow.

## Safety defaults

- Autonomous generation is disabled, including on existing V3 databases through
  a one-time migration.
- A cycle can render at most three discovery sketches.
- Live research must return at least three auditable source URLs or the cycle
  stops before image generation.
- Default daily API estimate guard is USD 2.
- Discovery dimensions, stone sizes and weights are explicitly estimates.

## Recommended first run

1. Deploy the package and confirm `Autonomous cycles enabled` is OFF.
2. Select `South Indian Gemstone` and one necklace category.
3. Leave weight and stone strategy on `Auto` for research-only discovery.
4. Run one controlled batch.
5. Review the research links and the maximum three sketches.
6. Mark each sketch Excellent, Usable or Reject before another batch.

The application produces concept sketches only. It does not create 3DM or claim
manufacturing-ready measurements.
