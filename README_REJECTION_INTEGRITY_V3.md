# Rejection Integrity v3

This build fixes the root cause that could make an owner-rejected design reappear after a quality-threshold or preset change.

## Permanent reject semantics
- `Reject` is terminal for visible-library purposes.
- Feedback is inserted and the design is hidden in the same database transaction.
- A database trigger enforces `visible=0`, `favorite=0`, `status=owner_rejected`.
- A second database trigger prevents any later UI/settings update from resurrecting a rejected design.
- Startup self-audit repairs contradictory historical rows automatically.
- Accepted Design Library queries and score-band counts independently exclude any design with reject feedback.
- Rejection reason/note remains stored for negative-learning in Deep mode.

## Root cause fixed
Earlier quality-threshold/preset changes recalculated `visible` for all scored designs. That could set a previously rejected row back to `visible=1`. This build makes threshold recalculation rejection-aware and also enforces the rule at the database layer.
