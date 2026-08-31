# Trend2Sketch Studio 95+ Diagnostic Fix

This build adds end-to-end stage logging and exposes exact cycle exceptions directly in the Studio dashboard.

Changes:
- Prints research, concept, scoring, rendering and worker errors to Render logs with flush enabled.
- Saves full failure stage/type/traceback in the cycle note.
- Shows latest failure details in a red alert + expandable panel in Studio.
- Explicitly detects a missing OpenAI API key.
- Logs both web-search failure and fallback failure separately.
- Keeps the 95+ quality gate, 300 concept pool, 30 max renders/cycle and budget/resource guards unchanged.
- Replaces deprecated Streamlit width usage.

Deploy by replacing the matching files in the GitHub repository, commit, wait for Render to redeploy, then run only one cycle if the worker does not automatically start one.
