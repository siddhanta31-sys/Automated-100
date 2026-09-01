# Deploy Trend2Sketch Studio from iPad

1. Download and unzip this package in Files.
2. In GitHub Safari, create/open a private repository or a new branch dedicated to Studio.
3. Upload every file from the package into the repository root and commit.
4. In Render, create a new Blueprint from that repository.
5. Enter `APP_PASSWORD` and `OPENAI_API_KEY`. Keep secrets only in Render.
6. Deploy. Do not delete the existing Auto100 service until Studio has completed several successful cycles.
7. Open the new Render URL in Safari. Share → Add to Home Screen.

The default Studio settings explore 300 concepts every 30 minutes, render at most 30 high-scoring candidates, and show only final scores of 95+.


## Foolproof Design OS update
Upload this build only after stopping/finishing a healthy current cycle. A genuinely stuck/timeout cycle may be interrupted. Keep the existing Render persistent disk and environment secrets. Do not delete the disk: it contains your design library, feedback and Design DNA.

After deployment, open My Design DNA, select/create a profile, upload 10-20 strong approved designs, and use Analyze & save. First production-learning test: Deep / 10 designs / threshold 75.
