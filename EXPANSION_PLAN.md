# Transaction Risk Gateway - Expansion Plan

## 1. Scalable Authentication System

### Current Issues
- No authentication at all on `/evaluate` endpoint
- No user session management
- No role-based access control (RBAC)

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────────┐ │
│  │ Rate Limit  │  │ API Key     │  │ JWT Token Auth             │ │
│  │ (100/min)  │  │ Validation │  │ (Short-lived access)      │ │
│  └─────────────┘  └─────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Authentication Service                      │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────────┐ │
│  │ OAuth2      │  │ API Key    │  │ API Key                    │ │
│  │ Password   │  │ Manager    │  │ Registry                   │ │
│  └─────────────┘  └─────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

**Add auth dependencies:**
```python
# api/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-Key")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return {"user_id": user_id, "permissions": payload.get("permissions", [])}
    except JWTError:
        raise credentials_exception
```

**Rate limiting per user:**
```python
# api/rate_limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from collections import defaultdict

class UserRateLimiter:
    def __init__(self):
        self.limiters = defaultdict(lambda: Limiter(key_func=get_remote_address))
    
    def get_limiter(self, user_id: str):
        return self.limiters[user_id]
```

---

## 2. PostgreSQL Migration

### Current Architecture (SQLite)
```
users.db ──► SQLite ──► Single file, no horizontal scaling
audit.db ──► SQLite ──► File locking issues under load
```

### Proposed Architecture (PostgreSQL)
```
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL Primary                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │
│  │ Users Table  │ │Transactions │ │ Audit Logs (Partitioned) │  │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Read Replicas
┌─────────────────────────────────────────────────────────────────┐
│                   PostgreSQL Replica 1, 2, n                  │
│              (Read queries, scaling reads)                     │
└─────────────────────────────────────────────────────────────────┘
```

### Schema Migration

```sql
-- users.sql
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    residence_country VARCHAR(2),
    known_countries VARCHAR(2)[],
    known_recipients VARCHAR(255)[],
    failed_attempts INTEGER DEFAULT 0,
    account_locked_until TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_users_country ON users(residence_country);
CREATE INDEX idx_users_locked ON users(account_locked_until) WHERE account_locked_until IS NOT NULL;

-- transactions.sql
CREATE TABLE transactions (
    transaction_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(user_id),
    amount DECIMAL(15,2),
    destination_country VARCHAR(2),
    destination_account VARCHAR(255),
    timestamp TIMESTAMP DEFAULT NOW(),
    decision VARCHAR(50),
    combined_risk_score DECIMAL(5,4),
    metadata JSONB
);

CREATE INDEX idx_transactions_user ON transactions(user_id, timestamp);
CREATE INDEX idx_transactions_timestamp ON transactions(timestamp);

-- audit_logs.sql (Partitioned by month)
CREATE TABLE audit_logs (
    id BIGSERIAL,
    transaction_id VARCHAR(255),
    user_id VARCHAR(255),
    timestamp TIMESTAMP,
    transaction JSONB,
    signals JSONB,
    decision VARCHAR(50),
    combined_risk_score DECIMAL(5,4),
    required_actions JSONB,
    reasoning TEXT,
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE audit_logs_2025_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Add TimescaleDB extension for time-series optimization
CREATE EXTENSION IF NOT EXISTS timescaledb;
SELECT create_hypertable('audit_logs', 'timestamp');
```

### Database Connection Pool

```python
# database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://user:password@localhost:5432/gateway"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    echo=os.getenv("SQL_ECHO", "false") == "true"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 3. Advanced ML Models

### Current State
- Single LogisticRegression model
- 5 features only
- No model versioning

### Proposed Multi-Model Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Model Ensemble                              │
│  ┌───────────────┐ ┌───────────────┐ ┌─────────────────────────┐  │
│  │ Rule-Based   │  │ Gradient     │  │ Anomaly Detection     │  │
│  │ Ensemble    │  │ Boosting     │  │ (Isolation Forest)    │  │
│  │              │  │ (XGBoost)    │  │                       │  │
│  └───────────────┘ └───────────────┘ └─────────────────────────┘  │
│                                                                  │
│  ┌───────────────┐ ┌───────────────┐ ┌─────────────────────────┐  │
│  │ Graph Neural │  │ Sequential   │  │ Ensemble               │  │
│  │ Network      │  │ Model (LSTM) │  │ Combiner                │  │
│  │              │  │              │  │ (Weighted Average)     │  │
│  └───────────────┘ └───────────────┘ └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Feature Engineering Expansion

```python
# features/engineer.py
class TransactionFeatureEngineer:
    def __init__(self, db_session):
        self.db = db_session
    
    def generate_features(self, transaction: dict, user: dict, historical_data: list) -> dict:
        features = {}
        
        # ──────────────────────────────────────────────────────────
        # 1. Transaction Features
        # ──────────────────────────────────────────────────────────
        features['amount'] = transaction['amount']
        features['amount_log'] = np.log1p(transaction['amount'])
        features['amount_percentile'] = self._calculate_percentile(
            transaction['amount'], user.get('transaction_history', [])
        )
        
        # ─────��─��──────────────────────────────────────────────────
        # 2. Velocity Features
        # ──────────────────────────────────────────────────────────
        tx_history = historical_data[-24*60:]  # Last 24 hours in minutes
        features['tx_count_1h'] = len([t for t in tx_history if t['timestamp'] > 1 hour ago])
        features['tx_count_24h'] = len(tx_history)
        features['amount_velocity_1h'] = sum(t['amount'] for t in tx_history if t['timestamp'] > 1 hour ago)
        features['amount_velocity_24h'] = sum(t['amount'] for t in tx_history)
        
        # ──────────────────────────────────────────────────────────
        # 3. Recipient Features
        # ──────────────────────────────────────────────────────────
        recipient = transaction.get('destination_account')
        features['recipient_known'] = recipient in user.get('known_recipients', [])
        features['recipient_transaction_count'] = self._count_transactions_to(recipient)
        features['recipient_account_age_days'] = self._get_account_age(recipient)
        features['recipient_risk_score'] = self._get_recipient_risk_score(recipient)
        
        # ──────────────────────────────────────────────────────────
        # 4. Geo Features
        # ──────────────────────────────────────────────────────────
        features['same_country'] = transaction.get('destination_country') == user.get('residence_country')
        features['high_risk_country'] = transaction.get('destination_country') in HIGH_RISK_COUNTRIES
        features['distance_from_residence'] = self._calculate_distance(
            user.get('residence_country'), 
            transaction.get('destination_country')
        )
        
        # ──────────────────────────────────────────────────────────
        # 5. Time-Based Features
        # ──────────────────────────────────────────────────────────
        tx_time = transaction.get('timestamp')
        features['is_business_hours'] = 9 <= tx_time.hour < 17
        features['is_weekend'] = tx_time.weekday() >= 5
        features['is_late_night'] = tx_time.hour < 6 or tx_time.hour > 22
        features['is_month_end'] = tx_time.day >= 28
        
        # ──────────────────────────────────────────────────────────
        # 6. Device/Session Features
        # ──────────────────────────────────────────────────────────
        features['new_device'] = transaction.get('device_fingerprint') not in user.get('known_devices', [])
        features['new_ip'] = transaction.get('ip_address') not in user.get('known_ips', [])
        features['isp_change'] = transaction.get('isp') != user.get('last_isp')
        
        # ──────────────────────────────────────────────────────────
        # 7. Behavioral Features
        # ──────────────────────────────────────────────────────────
        features['note_sentiment_score'] = self._analyze_sentiment(transaction.get('notes', ''))
        features['note_length'] = len(transaction.get('notes', ''))
        features['has_template_language'] = self._check_template_language(transaction.get('notes', ''))
        
        # ──────────────────────────────────────────────────────────
        # 8. Graph Features
        # ──────────────────────────────────────────────────────────
        recipient = transaction.get('destination_account')
        features['recipient_degree'] = self._get_graph_degree(recipient)
        features['recipient_fraud_count'] = self._get_fraud_count(recipient)
        features['is_first_party'] = self._is_first_party_transaction(user, recipient)
        
        return features
    
    def _calculate_percentile(self, amount, history):
        if not history:
            return 0.5
        amounts = [t['amount'] for t in history]
        return sum(a < amount for a in amounts) / len(amounts)
```

### Model Registry

```python
# ml/model_registry.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import mlflow

@dataclass
class ModelVersion:
    model_name: str
    version: int
    model_path: str
    metrics: dict
    trained_at: datetime
    feature_set: List[str]
    hyperparameters: dict

class ModelRegistry:
    def __init__(self, tracking_uri: str = "http://localhost:5000"):
        mlflow.set_tracking_uri(tracking_uri)
        self.client = mlflow.tracking.MlflowClient()
    
    def register_model(self, model_name: str, model_path: str, metrics: dict, feature_set: List[str]):
        version = self.client.create_model_version(model_name, model_path)
        
        # Log parameters
        with mlflow.start_run():
            mlflow.log_metrics(metrics)
            mlflow.log_param("feature_count", len(feature_set))
            mlflow.log_param("features", ",".join(feature_set))
        
        return version
    
    def get_best_model(self, model_name: str, metric: str = "f1_score") -> ModelVersion:
        # Get latest version with best metric
        pass
    
    def stage_model(self, model_name: str, version: int, stage: str = "production"):
        self.client.transition_model_version_stage(model_name, version, stage)
```

---

## 4. Complete Expanded Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         External Clients                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │
│  │ Mobile   │  │ Web      │  │ Backend │  │ Admin Dashboard   │    │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────���─���───────────────────────────────────────────────────────────────┐
│                     API Gateway (Nginx/Kong)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │ JWT Auth   │  │ Rate Limit │  │ API Key    │  │ IP Allowlist │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        Endpoints                                │   │
│  │  POST /evaluate    GET /metrics    GET /health    GET /audit    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Auth Service   │   │  Decision Engine│   │  Model Service  │
│  - JWT          │   │  - Rules        │   │  - XGBoost      │
│  - OAuth2       │   │  - ML Ensemble  │   │  - Isolation    │
│  - API Keys     │   │  - LLM          │   │    Forest       │
│                 │   │                 │   │  - Graph NN    │
└──────────────────┘   └──────────────────┘   └──────────────────┘
                                    │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ PostgreSQL      │   │ Cache (Redis)     │   │ MLflow          │
│ - User Profiles│   │ - Session Cache │   │ - Model Registry│
│ - Transactions │   │ - Rate Limit    ��   │ - Experiments   │
└──────────────────┘   └──────────────────┘   └──────────────────┘
        │                             │
        ▼                             ▼
┌──────────────────┐   ┌──────────────────┐
│ TimescaleDB     │   │ S3/CloudWatch  │
│ - Audit Logs   │   │ - Logs        │
│ - Time Series │   │ - Metrics     │
└──────────────────┘   └──────────────────┘
```

---

## 5. Implementation Priority

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| 1 | PostgreSQL Migration | Medium | High (scalability) |
| 2 | JWT Authentication | Low | High (security) |
| 3 | API Key + Rate Limiting | Low | High (security) |
| 4 | Feature Engineering | High | High (model accuracy) |
| 5 | XGBoost Model | Medium | High (model accuracy) |
| 6 | Model Versioning (MLflow) | Medium | Medium (operational) |
| 7 | Isolation Forest | Medium | Medium (model accuracy) |
| 8 | Graph Features | High | Medium (model accuracy) |
| 9 | Read Replicas | Medium | High (scalability) |
| 10 | Admin Dashboard | High | Low (operational) |

---

## 6. Technology Stack Summary

| Layer | Current | Recommended |
|-------|---------|-------------|
| Database | SQLite | PostgreSQL + TimescaleDB |
| Cache | None | Redis |
| Auth | None | JWT + OAuth2 |
| API Gateway | None | Kong or Nginx |
| ML Framework | Scikit-learn | XGBoost + PyTorch |
| Model Registry | None | MLflow |
| Feature Store | None | Feast |
| Monitoring | Print | Datadog/Prometheus |
| CI/CD | None | GitHub Actions |
