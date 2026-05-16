# Transaction Risk Gateway

A production-grade fraud detection microservice for fintech, designed to make safe decisions under uncertainty in real-time transaction processing.

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google-gemini)](https://ai.google.dev/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-%23F7931E.svg?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)

## Overview

The **Transaction Risk Gateway** is a highly concurrent, multi-layered security service that evaluates financial transactions for fraud using a combination of deterministic rules, machine learning anomaly detection, and generative AI behavioral analysis.

It is built entirely on asynchronous I/O using FastAPI, asyncpg, and SQLAlchemy 2.0, allowing for high-throughput decision-making while persisting immutable audit logs to a PostgreSQL database.

### Key Architecture: Multi-Layer Signal Aggregation
Unlike traditional systems that use weighted averages (which can dampen severe risks), this gateway uses a **maximum-signal approach**:
```python
combined_risk = min(1.0, max(rules_score, ml_score) + lm_boost)
```
This ensures that if *any* layer detects a critical threat, the transaction is immediately escalated to human review.

---

## Features & Deep Architecture

### 1. Deterministic Rules Layer
Acts as the first line of defense. It evaluates hard metrics:
- Amount thresholds and velocity checks.
- Novelty detection (new recipient, new country).
- Account age and historical failures.

### 2. Machine Learning Anomaly Detection
Provides probabilistic scoring and feature importance attribution via an integrated scikit-learn model. It evaluates statistical z-scores of transaction amounts against the user's historical baseline. 
*Note: The ML model (`ml_model.pkl`) must be trained locally for your environment. If it fails to load or is incompatible with the server's architecture, the system safely catches the `SystemError` and bypasses the ML layer to rely strictly on the Rules Layer.*

### 3. Generative AI Behavioral Analysis (LLM)
Leverages Google Gemini Pro to parse free-text transaction notes for social engineering patterns (e.g., "paying the IRS agent", "tech support refund") and returns a dynamic risk boost alongside a natural language rationale.

### 4. Fail-Safe Design & Graceful Degradation
The system is built to never crash the payment flow. If the ML model is missing, or if the LLM API times out, the engine defaults to a "safe mode" that relies entirely on deterministic rules and logs the fallback event in the audit trail. 

### 5. Immutable Audit Trail
Every single transaction, regardless of outcome, is saved to the PostgreSQL `audit_logs` table. This includes the exact input payload, the sub-scores of all three layers, the final combined score, and the generated text reasoning. 

---

## Tech Stack

- **Backend**: FastAPI, Uvicorn, Pydantic
- **Database**: PostgreSQL, SQLAlchemy 2.0 (Async), asyncpg
- **Machine Learning**: Scikit-Learn, Pandas, NumPy
- **Generative AI**: Google Gemini Pro (via `google-genai` SDK)
- **Rate Limiting**: slowapi

---

## Decision Logic

| Risk Score | Decision | Action |
|------------|----------|--------|
| `< 0.30` | **ALLOW** | Proceed immediately |
| `0.30 - 0.54`| **VERIFY** | Trigger MFA (Phone/Video) |
| `≥ 0.55` | **ESCALATE** | Manual Human Review |

---

## Known Architectural Bottlenecks & Future Improvements

As the system scales, the following areas represent technical debt and bottlenecks that must be addressed for high-volume enterprise deployment:

1. **The Cold Start Problem:** The strict rules engine heavily penalizes new accounts, new recipients, and new countries. A legitimate first-time user triggers all three simultaneously, forcing a 0.75 risk score and immediate escalation.
2. **Synchronous Execution Blocking the Async Loop:** The `ml_layer` and `rules_layer` run CPU-heavy operations synchronously. In FastAPI, this blocks the single-threaded event loop, delaying all other pending requests.
3. **Database Race Conditions:** User transaction history is loaded, appended, and saved back to a JSONB column. Concurrent requests by the same user will result in "Lost Updates".
4. **External LLM Latency:** Pausing a financial transaction to wait 1-5 seconds for Google Gemini degrades user experience and exhausts connection pools under load.
5. **The "Fat Row" Anti-Pattern:** Storing hundreds of transactions inside a single `JSONB` array in the `users` table causes massive serialization/deserialization overhead on every database read/write.

---

## Getting Started

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/transaction-risk-gateway.git
cd transaction-risk-gateway
python -m venv gateway_env
# On Windows:
gateway_env\Scripts\activate
# On Mac/Linux:
# source gateway_env/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the root directory:
```env
# Gemini API Key (free tier)
GEMINI_API_KEY=your_gemini_api_key

# Gateway API Key (sent as X-API-Key header by clients)
GATEWAY_API_KEY=gateway-dev-key-2024

# Local PostgreSQL (via Docker)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5433/gateway
```

### 3. Start PostgreSQL
```bash
docker-compose up -d
```
*You can connect to this database using an IDE like DataGrip on `localhost:5433` with user `postgres` and password `password`.*

### 4. Run the API Server
```bash
uvicorn api.main:app --reload
```

### 5. Test the Endpoint
In a separate terminal, run the included test script to simulate a transaction and watch the engine evaluate the risk:
```bash
python test_transaction.py
```
Afterward, check your PostgreSQL database's `audit_logs` table to see the exact reasoning the engine used to make its decision.

---

## License
MIT License - See LICENSE for details.
