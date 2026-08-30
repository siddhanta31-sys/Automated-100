# Update your existing Render deployment

1. Unzip this package.
2. Replace the files in your existing private GitHub Trend2Sketch repository.
3. Commit to `main`.
4. Render will redeploy automatically.

## Required Render Environment
- APP_PASSWORD
- OPENAI_API_KEY

## Automatic generation
- AUTO_INTERVAL_MINUTES=30
- AUTO_RUN_ON_START=true
- GENERATION_CONCURRENCY=4
- OPENAI_IMAGE_QUALITY=low

## Output per batch
- 50 Diamond designs
- 50 South Indian gemstone designs
- 100 total
- All 10 categories covered in both lanes
- 5 weight bands per category

## Optional email
- SEND_TO_EMAIL
- RESEND_API_KEY
- SEND_FROM_EMAIL
- APP_PUBLIC_URL

Open the Render URL in Safari -> Share -> Add to Home Screen.
