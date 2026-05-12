# Design Philosophy: Explainable Transaction Risk Gateway

## Core Insight
Fraud detection systems optimize for *prediction accuracy*.
This system optimizes for *decision quality under uncertainty*.

## Why This Matters
In fintech:
- False negative (allow fraud): Catastrophic (financial loss, regulatory problem)
- False positive (block good customer): Recoverable (customer can appeal)

Therefore: system should bias toward false positives.

## Key Design Decisions

### 1. Maximum Signal Approach
When signals disagree (rules say risky, ML says normal), we don't average.
We take the maximum. Why? Because disagreement is interesting.

If rules know this user and scream "fraud," but ML says "normal," 
we escalate—not because either is right, but because they disagree.

### 2. Tolerance Bounds
Thresholds aren't hard lines. Transactions near a threshold are uncertain.
When uncertain, we escalate to humans (not allow, not deny randomly).

### 3. Fail Safe by Default
ML model down? Use rules layer only.
LLM timeout? Don't wait forever, use fallback.
Database connection fails? Don't guess, escalate.

Every failure mode has a safe default.

### 4. Full Auditability
Every decision is logged with: inputs, all signals, reasoning, outcome.
When asked "why was I blocked?" we can show them exactly why.

## Anti-Patterns We Avoid
- Trusting model confidence blindly
- Averaging weak consensus
- Guessing when uncertain
- Operating without audit trail
- Pretending to be perfect

## Success Criteria
Not: "Catch 99% of fraud"
But: "Make safe decisions when uncertain, allow appeals, remain explainable"
