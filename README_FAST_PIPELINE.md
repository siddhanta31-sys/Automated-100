# Trend2Sketch Fast Pipeline

This build accelerates the hardened Advanced Studio without removing reliability controls.

## Speed changes
- Adaptive concept pool based on requested design count.
- Parallel concept discovery (Fast 4 workers, Balanced 3, Deep 2).
- Parallel concept scoring.
- Live concept/scoring progress written to the dashboard.
- Matching research is cached: Fast up to 6h, Balanced up to 2h, Deep always researches fresh.
- Fast/Balanced rendering uses controlled parallelism, while existing resource and budget guards remain active.
- In-app Worker Speed selector: Fast / Balanced / Deep. No redeployment needed to switch modes.

## Recommended
Use **Balanced** for normal autonomous work. Use **Fast** for trials. Use **Deep** when you want the broadest concept exploration and can wait longer.
