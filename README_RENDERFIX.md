# Trend2Sketch Advanced Studio — Render Fix

This is the advanced Rank100/95Gate Studio build, not the old Auto100 build.

Key behavior:
- researches a 300-concept pool each cycle
- dynamic Diamond and South Indian Gemstone concept discovery
- ranks concepts before rendering
- renders up to the top 100 concepts subject to budget/resource guards
- applies the strict 95+ visibility gate after finished-design visual scoring
- runs autonomously every 30 minutes
- disables Streamlit file watching to avoid Render inotify instance-limit failures

The background supervisor/worker remains enabled.
