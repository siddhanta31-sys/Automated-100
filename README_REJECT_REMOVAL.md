# Reject-removal update

When the owner saves a rejection from the Accepted Design Library:

- the rejection verdict, reason, and optional note are retained for Design Director learning;
- the design is immediately marked `visible=0`, `favorite=0`, `status=owner_rejected`;
- it disappears from the Accepted Design Library after the automatic rerun;
- it is excluded from the score-calibration library counts;
- the underlying record/image is retained internally so the system can learn what not to generate again.
