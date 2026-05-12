# How Decisions Are Made

## The Formula (Simple)
`combined_risk = max(rules_score, ml_score) + lm_boost`

Where:
- `rules_score`: How many rule thresholds trigger? (0.0-0.8)
- `ml_score`: How anomalous is this? (0.0-0.9)
- `lm_boost`: Any behavioral red flags? (0.0-0.2)

## The Decision Logic (Simple)
```python
if combined_risk < 0.30:
    → ALLOW (low risk)

elif combined_risk < 0.55:
    → REQUIRE_VERIFICATION (medium risk, but suspicious)

else:
    → ESCALATE_TO_HUMAN (high risk, needs human judgment)
```

## Why Each Decision
- **ALLOW**: Rules and ML both say this looks normal. User has history.
- **VERIFY**: Something's odd (new recipient, unusual amount) but not screaming.
  Require 2FA or security questions.
- **ESCALATE**: Either rules or ML (or both) flag this as risky. 
  Only human should approve.

## Edge Cases
- **User has no history**: New account is higher risk automatically
- **ML model is down**: Fall back to rules only (safe)
- **Score is on threshold boundary**: Escalate (when uncertain, ask human)
- **Multiple failed attempts**: Lock account (prevent brute force)

## What This Prevents
- Fraud getting through (rules catch patterns)
- Unusual but legitimate transactions getting blocked unnecessarily (verify instead of escalate)
- System hanging waiting for slow APIs (timeouts + fallbacks)
- Audit trail disappearing (everything logged)
