# Trend2Sketch Studio — Ranked Render Update

This update fixes the zero-render problem caused by requiring a concept to score 95+ before image generation.

New pipeline:
1. Research and discover ~300 concepts.
2. Score all concepts with the design-intelligence model.
3. Rank novel concepts from highest to lowest.
4. Render up to the top 100 concepts per cycle, subject to the daily API budget and system safeguards.
5. Visually score the finished design.
6. Compute a final 1–100 score weighted 20% concept intelligence + 80% finished-design visual review.
7. Show only finished designs with final score >=95.

The 95+ quality gate is preserved. It now happens at the correct stage: after a design is actually rendered.

Cost protection remains active through DAILY_API_BUDGET_USD. With the default estimated image cost of $0.03, a 100-image cycle is estimated at roughly $3 plus text/research usage, but actual provider billing can differ.
