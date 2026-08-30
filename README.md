# Trend2Sketch Auto100 — iPad Autonomous Edition

This edition generates **100 original jewellery sketches every 30 minutes**:

- **50 Diamond jewellery designs**
- **50 South Indian gemstone jewellery designs**

No daily user input is required.

## Every batch covers all 10 categories in BOTH lanes

Each category gets 5 weight bands, so:

10 categories × 5 weight bands = 50 Diamond designs  
10 categories × 5 weight bands = 50 South Indian gemstone designs  
**Total = 100 designs per batch**

### Categories
1. Bangle
2. Earring
3. Jhumka
4. Chandbali
5. Ring
6. Short Necklace
7. Long Necklace
8. Haram
9. Bridal Set
10. Vaddanam

## Autonomous workflow
Every 30 minutes:
1. Researches current public catalogue signals from Tanishq, Malabar Gold & Diamonds, Kalyan Jewellers and Joyalukkas.
2. Separates Diamond trends from South Indian gemstone trends.
3. Ranks trends by inferred commercial potential.
4. Generates 100 original sketches across the full category/weight matrix.
5. Saves all designs in the persistent library.
6. Optionally emails a batch summary and a link to the app.

## Required Render variables
- APP_PASSWORD
- OPENAI_API_KEY

## Recommended
- AUTO_INTERVAL_MINUTES=30
- OPENAI_TEXT_MODEL=gpt-5.6-luna
- OPENAI_IMAGE_MODEL=gpt-image-2
- OPENAI_IMAGE_QUALITY=low
- GENERATION_CONCURRENCY=4

## Optional email delivery
- SEND_TO_EMAIL
- RESEND_API_KEY
- SEND_FROM_EMAIL
- APP_PUBLIC_URL

## Cost warning
100 sketches every 30 minutes = **4,800 generated images per day** if it runs continuously.
Start on low image quality and monitor API costs carefully.

## Commercial scoring
The app estimates likely commercial potential from current public catalogue signals.
It cannot guarantee a design will become a fast seller. Accuracy will improve significantly once your own sales/order data is connected.
