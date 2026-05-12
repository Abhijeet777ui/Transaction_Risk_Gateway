# Real Scenario: High-Risk International Wire

## The Transaction
- User: John, UK-based, £40k salary, regular customer
- Amount: £50,000 (1.25x annual salary)
- Recipient: New (never sent to before)
- Destination: Nigeria
- Time: 3 AM (unusual)
- Notes: "urgent, pls send fast"

## What Each Layer Detects

### Rules Layer
- Amount high (£50k vs typical £500-2000) → +0.30 risk
- New recipient → +0.30 risk
- New country (Nigeria) → +0.20 risk
- **Total rule score: 0.80**

**Why?** These are pattern matches. We've seen fraud that looks like this before.

### ML Layer
- User's typical amount: £1,500 (percentile: 0.02)
- User's recipients: 5 known (this is new: percentile 1.0)
- User's countries: 2 (GB, US) (Nigeria is new: percentile 1.0)
- User typically transacts 9-5, this is 3 AM
- **Total anomaly score: 0.87**

**Why?** This is radically different from what we've learned about this user.

### LLM Layer
- "urgent" language detected (social engineering indicator)
- 3 AM timing (unusual for legitimate banking)
- Destination Nigeria (high fraud country)
- **Risk boost: +0.15**

**Why?** Behavioral cues suggest possible account compromise or social engineering.

## The Decision
```python
combined_risk = max(0.80, 0.87) + 0.15 = 1.0 (capped at 1.0)
Score: 1.0 > 0.54 threshold
Decision: ESCALATE_TO_HUMAN
```

## What Happens Next
1. System flags for human review
2. Fraud team sees: "High-risk international wire, new recipient, urgency language"
3. They call John's phone number on file
4. John says: "I didn't initiate this! My password was compromised!"
5. System: Blocks transaction, resets credentials, sends security alert
6. John: Safe. Transaction prevented.

## What This Shows
- Rules caught it (pattern match)
- ML confirmed (massive deviation from normal)
- LLM added explanation (why it's suspicious)
- Human made final call (prevented fraud)
- System learned this recipient is now flagged for future

This is exactly what the system is designed to do.
