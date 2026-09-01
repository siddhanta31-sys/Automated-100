# Render Progress upgrade

Adds live rendering visibility without changing the design intelligence pipeline.

- Render Logs now print rendering start, every completed image job, accepted/rejected/failed counts, elapsed time and ETA.
- Advanced Studio shows a live progress bar while a cycle is in the rendering stage.
- Cycle notes persist the latest progress so refresh/reconnect does not hide worker state.
- Existing speed modes, category controls, quality threshold, autonomous worker, retry/recovery, budget guard and single-cycle lock remain unchanged.
