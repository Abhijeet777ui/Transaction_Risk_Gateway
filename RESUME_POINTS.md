# Transaction Risk Gateway - Resume Points

## Project Overview
A production-grade fraud detection microservice for fintech, designed to make safe decisions under uncertainty in real-time transaction processing.

---

## Technical Skills Demonstrated

### Backend Development
- Built REST API with **FastAPI** supporting synchronous and async endpoints
- Implemented multi-layer signal processing pipeline (Rules → ML → LLM)
- Created configurable decision engine with threshold-based routing
- Designed fail-safe architecture with graceful degradation

### Data Engineering
- Migrated from **SQLite** to **PostgreSQL** using **SQLAlchemy 2.0 (Async)** for production-scale concurrency
- Implemented asynchronous database drivers (**asyncpg**) to handle high-throughput transaction logging
- Established structured database migration patterns for schema evolution and maintainability
- Built user profile manager for tracking transaction history and behavioral patterns
- Created structured schema for audit trails with full decision traceability

### Machine Learning Integration
- Integrated pre-trained **scikit-learn** model for anomaly detection
- Engineered features (Z-score, velocity, recipient/country novelty)
- Implemented model fallback when unavailable

### Security & Fraud Prevention
- Designed risk scoring algorithm with configurable thresholds
- Implemented multi-factor verification workflow (2FA, phone, video verification)
- Built account lockout mechanism for brute-force prevention

---

## Architecture Highlights

### Multi-Layer Signal Aggregation
```
combined_risk = min(1.0, max(rules_score, ml_score) + lm_boost)
```
- **Key insight**: Used maximum signal instead of weighted average to prevent dampening severe risks
- Prevents single-point-of-failure in fraud detection

### Decision Routing
| Risk Score | Decision |
|------------|----------|
| < 0.30 | ALLOW |
| 0.30 - 0.54 | REQUIRE_VERIFICATION |
| ≥ 0.55 | ESCALATE_TO_HUMAN |

### Async I/O Pipeline
- Optimized the entire decision engine with **Python asyncio**, enabling non-blocking database and API calls
- ML model unavailable → Fall back to rules-only scoring
- LLM timeout → Skip behavioral analysis, continue with rules+ML
- Database error → Auto-escalate to human review
- When uncertain → Bias toward false positives (safer)

---

## Key Features Implemented

1. **Deterministic Rules Layer**
   - Amount thresholds (medium/high)
   - New recipient/country detection
   - Velocity checking
   - Account age verification
   - Time-of-day anomaly detection

2. **ML Anomaly Detection Layer**
   - Feature engineering (amount Z-score, novelty flags)
   - Probability-based scoring
   - Feature importance attribution

3. **Behavioral Analysis Layer (LLM)**
   - Integrated **Google Gemini Pro** for real-time risk advisory
   - Transaction context analysis with natural language rationales
   - Social engineering indicator detection
   - Risk boost amplification

4. **Audit & Compliance**
   - Full decision traceability
   - Signal logging (all inputs, outputs, reasoning)
   - Appeal mechanism support

---

## Problem-Solving Highlights

### Problem: Structural Risk Score Cap
- **Issue**: Weighted average made it impossible to escalate high-risk transactions
- **Solution**: Replaced with maximum-based formula
- **Learning**: Design for worst-case, not average-case

### Problem: Floating Point Precision
- **Issue**: `0.15 + 0.30 + 0.20 = 0.6499...` failed boundary checks
- **Solution**: Implemented tolerance bounds (`±0.01`)
- **Learning**: Financial systems need exact boundary handling

### Problem: Cascading Failures
- **Issue**: Single layer failure could block legitimate users
- **Solution**: Graceful degradation with safe defaults
- **Learning**: Fail-safe by default, never guess

---

## Business Impact
- Prevents financial loss from fraud while minimizing false positives
- Provides explainable decisions for regulatory compliance
- Enables customer appeals with full audit trails
- Protects against account compromise and social engineering

---

## Additional Metrics & Features Implemented

### Performance & Operational Metrics
- **Real-time request tracking**: Total requests, allows, verifications, escalations, and error counts
- **Fallback monitoring**: Track ML/LLM/database fallbacks separately for system health analysis
- **Decision distribution**: Monitor approval vs. verification vs. escalation ratios

### Risk Scoring & Detection Metrics
- **Amount-based thresholds**: Medium (>£5,000) and high (>£10,000) risk scoring
- **Velocity checks**: Transactions per hour and per 24-hour window limits
- **Novelty detection**: New recipient and new country risk factors
- **Account age verification**: Flag transactions from accounts < 7 days old
- **Time-of-day anomaly**: Late-night hour unusual activity detection
- **Failed attempt tracking**: Brute-force prevention with account lockout after 3 failures

### ML Model Metrics
- **Z-score feature engineering**: Statistical anomaly scoring based on user's transaction history
- **Feature importance**: Attribute which features contributed to risk score
- **Model fallback**: Graceful degradation when ML model unavailable

### LLM Behavioral Analysis Metrics
- **Risk boost scoring**: Advisory risk amplification from behavioral analysis
- **Social engineering indicators**: Detection of manipulation patterns
- **Timeout handling**: Skip LLM analysis with fallback when timeout occurs

---

## Resume Bullet Points (Ready to Use)

1. **Designed and implemented a production-grade fraud detection microservice** using FastAPI, handling real-time transaction risk evaluation with multi-layer signal processing (Rules + ML + LLM).

2. **Built a fail-safe decision engine** with configurable thresholds and graceful degradation, ensuring system always defaults to safe behavior (bias toward false positives) when uncertain or component failure occurs.

3. **Implemented multi-layer risk aggregation architecture** replacing weighted averaging with maximum-signal approach to prevent dampening severe fraud signals and ensure high-risk transactions escalate to human review.

4. **Developed SQLite-based audit logging system** recording all transaction decisions with full traceability (inputs, signals, reasoning, outcome) enabling compliance reporting and customer appeals.

5. **Integrated scikit-learn anomaly detection model** with feature engineering pipeline (amount Z-score, velocity, novelty detection), providing probabilistic fraud scoring with feature importance attribution.

6. **Created user profile management system** tracking transaction history, known recipients/countries, and behavioral patterns to detect deviations from individual baselines.

7. **Implemented verification workflow** with multi-factor options (2FA, phone, video verification) for medium-risk transactions, reducing customer friction while maintaining security.

8. **Solved architectural risk score capping** by identifying weighted average flaw (max score 0.50) and replacing with max-based formula enabling true escalation of high-risk transactions.

9. **Implemented comprehensive operational metrics** tracking request distribution (allow/verify/escalate), fallback rates (ML/LLM/DB), and error rates for system health monitoring and alerting.

10. **Built multi-factor verification workflow** with progressive friction levels (user verification → phone → video → email) based on risk factors like transaction amount and destination country novelty.

11. **Designed account lockout mechanism** preventing brute-force attacks by tracking failed attempts and auto-locking after 3 failures with configurable duration.

12. **Implemented tolerance-based boundary handling** (±0.01) for floating-point precision issues in financial boundary checks.

13. **Created configurable decision thresholds** (allow < 0.30, verify 0.30-0.54, escalate ≥ 0.55) for risk-based routing with uncertainty bias toward safer decisions in ambiguous ranges.

14. **Architected and executed the migration from SQLite to PostgreSQL** using **SQLAlchemy 2.0 (Async)**, enabling production-grade concurrency and robust data persistence for high-volume transaction processing.

15. **Integrated Google Gemini Pro LLM** as a behavioral analysis layer, providing advisory risk signals and explainable natural language rationales for complex transaction patterns.

16. **Hardened system observability** by implementing structured logging, ensuring every stage of the multi-layer risk evaluation is fully auditable and monitorable in production environments.

17. **Implemented a formal database migration framework** to manage schema evolutions securely, ensuring zero-downtime deployments and data integrity.

---

## Full Tech Stack
- **Backend**: FastAPI (Asynchronous Python 3.10+), Uvicorn (ASGI)
- **Database**: PostgreSQL (Primary Storage), SQLAlchemy 2.0 (Async ORM), asyncpg (PostgreSQL Driver)
- **Machine Learning**: Scikit-learn (Anomaly Detection), Pandas, NumPy
- **Generative AI**: Google Gemini Pro (Behavioral Advisory Signal), OpenAI & Anthropic integration support
- **Security & Ops**: SlowAPI (Rate Limiting), Pydantic (Data Validation), python-dotenv (Environment management)
- **Testing & UI**: Pytest (Testing Framework), Streamlit (Internal Monitoring/Dashboard)
- **Architecture**: Async I/O pipeline, Fallback/Graceful degradation patterns, Structured DB migrations

