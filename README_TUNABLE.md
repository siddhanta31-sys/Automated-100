# Trend2Sketch Advanced Studio — Tunable Build

This build adds persistent in-app controls so ordinary quality testing no longer requires GitHub/Render redeployment.

## Live controls
- Quality acceptance score: 75–100
- Maximum renders per cycle: 5–100
- Pause/resume autonomous scheduled cycles
- Trial preset: 75 score / 10 renders
- Review preset: 85 score / 30 renders
- Production preset: 95 score / 100 renders

Settings are stored in the persistent SQLite database on the Render disk. Existing rendered designs are reclassified immediately when the acceptance threshold changes; this costs no API calls.

The Design Library also has a separate Review Floor (75–100), allowing side-by-side calibration of lower/higher scored designs without changing the actual acceptance threshold.

The existing autonomous research, 300-concept discovery, novelty screening, ranking, visual scoring, daily budget guard, persistent storage, and Streamlit watcher fix remain intact.


## Exact design-count control
The Live Studio Controls now include **Number of designs to generate per cycle**, adjustable from **1 to 100 in increments of 1**. The setting is persisted in the database and is read by both manual and autonomous cycles, so no redeployment is needed when changing the count.
