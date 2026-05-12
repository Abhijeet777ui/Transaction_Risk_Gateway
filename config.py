"""Configuration for Transaction Risk Gateway"""

RULES = {
    "AMOUNT_THRESHOLD_HIGH": 10000,      # £
    "AMOUNT_THRESHOLD_MEDIUM": 5000,
    "VELOCITY_MAX_PER_HOUR": 5,
    "VELOCITY_MAX_PER_24H": 20,
    "MINIMUM_ACCOUNT_AGE_DAYS": 7,
    "NEW_RECIPIENT_RISK": 0.3,
    "NEW_COUNTRY_RISK": 0.2,
    "ACCOUNT_LOCK_THRESHOLD": 3,         # 3 failures = lock
    "ACCOUNT_LOCK_DURATION_MINUTES": 60,
}

ML = {
    "MODEL_PATH": "models/ml_model.pkl",
    "ANOMALY_THRESHOLD": 0.85,
}

LLM = {
    "ENABLED": True,
    "PROVIDER": "gemini",   # 'gemini' (free) or 'openai' (paid)
    "TIMEOUT_SECONDS": 5,
    "MAX_RISK_BOOST": 0.2,
}

DECISION_ENGINE = {
    "ALLOW_THRESHOLD": 0.3,
    "VERIFY_THRESHOLD": 0.55,
    "ESCALATE_THRESHOLD": 0.55,
}

AUDIT = {
    "DATABASE_PATH": "audit.db",
    "ENABLE_LOGGING": True,
}

API = {
    "HOST": "0.0.0.0",
    "PORT": 8000,
    "RELOAD": False,
}

def validate_config():
    allow = DECISION_ENGINE.get('ALLOW_THRESHOLD', 0.0)
    verify = DECISION_ENGINE.get('VERIFY_THRESHOLD', 0.0)
    escalate = DECISION_ENGINE.get('ESCALATE_THRESHOLD', 0.0)
    assert 0.0 <= allow <= verify <= escalate <= 1.0, f"Invalid threshold bounds: allow={allow}, verify={verify}, escalate={escalate}"
