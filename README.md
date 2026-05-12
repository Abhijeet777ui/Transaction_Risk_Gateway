# 🛡️ Transaction Risk Gateway

A production-grade fraud detection microservice for fintech, designed to make safe decisions under uncertainty in real-time transaction processing.

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google-gemini)](https://ai.google.dev/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-%23F7931E.svg?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)

## 🚀 Overview

The **Transaction Risk Gateway** is a multi-layered security service that evaluates financial transactions for fraud using a combination of deterministic rules, machine learning anomaly detection, and generative AI behavioral analysis.

### Key Architecture: Multi-Layer Signal Aggregation
Unlike traditional systems that use weighted averages (which can dampen severe risks), this gateway uses a **maximum-signal approach**:
```python
combined_risk = min(1.0, max(rules_score, ml_score) + lm_boost)
```
This ensures that if *any* layer detects a critical threat, the transaction is immediately escalated.

---

## ✨ Features

- **🛡️ Deterministic Rules Layer**: Amount thresholds, velocity checks, novelty detection (new recipient/country), and account age verification.
- **🤖 ML Anomaly Detection**: Integrated scikit-learn model providing probabilistic scoring and feature importance attribution.
- **🧠 Behavioral Analysis (LLM)**: Leverages **Google Gemini Pro** to analyze transaction notes for social engineering patterns and provides natural language rationales.
- **🔄 Fail-Safe Design**: Graceful degradation—if the ML or LLM layers fail, the system falls back to rules-based scoring with an "uncertainty bias" toward safety.
- **📊 Audit & Compliance**: Full decision traceability with every signal, rationale, and outcome logged for regulatory review.
- **⚡ Async I/O**: Fully asynchronous pipeline using `FastAPI`, `SQLAlchemy 2.0`, and `asyncpg` for high-throughput performance.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, Uvicorn, Pydantic
- **Database**: PostgreSQL, SQLAlchemy 2.0 (Async), asyncpg
- **Machine Learning**: Scikit-Learn, Pandas, NumPy
- **Generative AI**: Google Gemini Pro (via `google-genai` SDK)
- **Observability**: Structured Logging, decision distribution monitoring
- **Infrastructure**: Docker & Docker Compose

---

## 🚦 Decision Logic

| Risk Score | Decision | Action |
|------------|----------|--------|
| `< 0.30` | **ALLOW** | Proceed immediately |
| `0.30 - 0.54`| **VERIFY** | Trigger MFA (Phone/Video) |
| `≥ 0.55` | **ESCALATE** | Manual Human Review |

---

## 🛠️ Getting Started

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/transaction-risk-gateway.git
cd transaction-risk-gateway
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file:
```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/gateway
GEMINI_API_KEY=your_api_key_here
```

### 3. Start PostgreSQL
```bash
docker-compose up -d
```

### 4. Run the API
```bash
uvicorn main:app --reload
```

---

## 📈 Roadmap & Future Goals
- [ ] Implement Redis-based rate limiting
- [ ] Add real-time dashboard with Streamlit
- [ ] Expand ML layer to include Graph Neural Networks (GNN) for link analysis
- [ ] Implement automated "Appeal" workflow for users

---

## ⚖️ License
MIT License - See [LICENSE](LICENSE) for details.
