# Deploy Trend2Sketch Studio from iPad

1. Download and unzip this package in Files.
2. In GitHub Safari, create/open a private repository or a new branch dedicated to Studio.
3. Upload every file from the package into the repository root and commit.
4. In Render, create a new Blueprint from that repository.
5. Enter `APP_PASSWORD` and `OPENAI_API_KEY`. Keep secrets only in Render.
6. Deploy. Do not delete the existing Auto100 service until Studio has completed several successful cycles.
7. Open the new Render URL in Safari. Share → Add to Home Screen.

The default Studio settings explore 300 concepts every 30 minutes, render at most 30 high-scoring candidates, and show only final scores of 95+.
