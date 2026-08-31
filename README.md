# Trend2Sketch Studio

A next-generation autonomous jewellery concept platform focused on dynamic concept discovery rather than a fixed category matrix.

## What changed from Auto100
- Researches and discovers jewellery families/sub-families itself.
- Explores ~300 concepts per cycle by default.
- Strict 1–100 design intelligence score.
- Only designs scoring 95+ after concept + visual checks are visible.
- Novelty filter reduces repetitive concepts.
- Cost guard pauses generation at the configured daily estimate budget.
- RAM/disk guard adapts generation concurrency.
- Worker supervisor automatically restarts the background worker after a crash.
- SQLite WAL + persistent disk protect state across app restarts.
- Old non-favourite renders can be archived after a retention period.

## Important
The 95+ score is an internal design-quality/commercial-potential score, not a guarantee of sales.
This package generates design concepts/images; it does not yet create production-ready 3DM geometry. CAD/3DM is a separate future engine and should be validated before manufacturing.

## Render deployment
1. Create a new private GitHub repo or branch and upload all files to the repo root.
2. Create a Render Blueprint from `render.yaml`.
3. Set `APP_PASSWORD` and `OPENAI_API_KEY` in Render; never commit API keys.
4. Deploy.
5. After deployment, optionally set `APP_PUBLIC_URL` to the Render URL.

Recommended first test: keep defaults for 24 hours before increasing render volume or budget.

## Live Product Development Selector
The Studio now includes persistent multi-select controls for design lanes and product categories. Choose one or many categories, use quick presets, or add custom categories without editing code or redeploying. The worker reads the saved selection at the start of every autonomous or manual cycle and constrains research/concept generation accordingly. Leaving the category selection empty enables dynamic auto-discovery.
