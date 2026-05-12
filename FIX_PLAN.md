# Transaction Risk Gateway - Fix Plan

## Critical / High Priority Issues

---

### Issue 1: Stale Config Values (config.py)
**Problem:** RULES_WEIGHT, ML_WEIGHT, LLM_WEIGHT are defined in config.py but ignored by engine.py which uses max() formula.

**Fix:** Remove the unused weight variables from config.py since they're misleading.

```python
# In config.py, remove these lines (or mark as deprecated):
"RULES_WEIGHT": 0.5,
"ML_WEIGHT": 0.3,
"LLM_WEIGHT": 0.2,
```

---

### Issue 2: Threshold Inconsistency
**Problem:** 
- config.py: VERIFY_THRESHOLD = 0.55
- DECISION_LOGIC.md: escalation at > 0.54
- engine.py: adds 0.01 tolerance = 0.56

**Fix:** Unify to a single threshold. Use 0.55 and remove the inconsistent tolerance logic.

In engine.py, replace:
```python
THRESHOLD_TOLERANCE = 0.01
MID_RANGE_LOWER = self.allow_threshold - THRESHOLD_TOLERANCE
```

With cleaner logic:
```python
# Use exact thresholds from config without tolerance
ALLOW_CUTOFF = self.allow_threshold  # 0.30
ESCALATE_CUTOFF = self.verify_threshold  # 0.55 (unified)
```

Update DECISION_LOGIC.md to match:
```
if combined_risk < 0.30:
    → ALLOW

elif combined_risk < 0.55:
    → REQUIRE_VERIFICATION

else:
    → ESCALATE_TO_HUMAN
```

---

### Issue 3: Floating Point Precision Bugs
**Problem:** 0.15 + 0.30 + 0.20 = 0.6499999999999999 instead of 0.65

**Fix:** Use `round()` for all score calculations.

In engine.py, modify the score calculation:
```python
# Calculate Combined Risk Score
rules_risk = rules_signal.get('risk_score', 0.0)
ml_risk = ml_signal.get('anomaly_score')
lm_risk_boost = lm_signal.get('risk_boost', 0.0)

ml_unavailable = ml_risk is None
base_risk = rules_risk if ml_unavailable else max(rules_risk, ml_risk)

# FIX: Round to 2 decimal places to avoid floating point errors
combined_risk = round(min(1.0, base_risk + lm_risk_boost), 2)
```

---

### Issue 4: Deprecated OpenAI API
**Problem:** Uses legacy openai.ChatCompletion.create() instead of client-based API (openai>=1.0)

**Fix:** Update lm_layer.py to use the new client-based API:

```python
def _call_openai(self, context) -> dict:
    try:
        from openai import OpenAI  # New client-based import
        
        if not self.api_key:
            return self._default_response_dict("OpenAI API key missing")
        
        client = OpenAI(api_key=self.api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": str(context)}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        analysis = json.loads(content)
        
        return {
            'flags': analysis.get('behavioral_flags', []),
            'narrative': analysis.get('explanation', ''),
            'risk_boost': min(float(analysis.get('risk_boost', 0)), 0.2)
        }
        
    except Exception as e:
        return self._default_response_dict(f"LLM API error: {e}")
```

---

### Issue 5: Binary DBs in Repo
**Problem:** audit.db and users.db committed to version control

**Fix:** Add to .gitignore:

```
# Ignore database files
*.db
*.sqlite
*.sqlite3
```

Create a .gitignore file in the root:
```
transaction-risk-gateway/
*.db
*.sqlite
*.sqlite3
__pycache__/
*.pyc
*.pyo
.env
.venv
env/
venv/
```

---

## Medium Priority Issues

---

### Issue 6: Blocking LLM Calls
**Problem:** LMLayer.evaluate() is synchronous and will block FastAPI event loop

**Fix:** Convert to async using run_in_executor:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class LMLayer:
    def __init__(self, provider: str, api_key: str = None):
        self.provider = provider
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def evaluate_async(self, transaction: dict, user: dict, signals_from_previous_layers: dict) -> dict:
        """Async wrapper for LLM evaluation"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.evaluate,
            transaction,
            user,
            signals_from_previous_layers
        )
    
    # Keep sync version for backward compatibility
    def evaluate(self, transaction: dict, user: dict, signals_from_previous_layers: dict) -> dict:
        # (existing implementation)
        pass
```

Then update main.py to use the async version:
```python
lm_signal = await lm_layer.evaluate_async(transaction, user_dict, {'rules': rules_signal, 'ml': ml_signal})
```

---

### Issue 7: Logic Bug - Double-Counting Failed Attempts
**Problem:** main.py calls increment_failed_attempt() after account is already locked

**Fix:** Only record transaction, don't increment on lock:

```python
# In main.py, replace this:
if decision_str == 'lock_account':
    user_manager.increment_failed_attempt(request.user_id)
else:
    user_manager.record_transaction(request.user_id, transaction, decision_str)

# With this:
if decision_str != 'lock_account':
    user_manager.record_transaction(request.user_id, transaction, decision_str)
# The lock_account case is handled by rules_layer when it returns action_override='lock_account'
```

---

### Issue 8: API Security (No Auth/Rate Limiting)
**Problem:** /evaluate endpoint has no authentication or rate limiting

**Fix:** Add FastAPI security dependencies:

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Explainable Transaction Risk Gateway")

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Depends(APIKeyHeader)):
    if api_key != os.getenv("GATEWAY_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.post("/evaluate")
@limiter.limit("100/minute")  # Rate limit: 100 requests per minute
async def evaluate_transaction(request: TransactionRequest, api_key: str = Depends(verify_api_key)):
    # ... existing code
```

---

### Issue 9: SQLite for Production (Architectural)
**Problem:** Uses SQLite which won't scale

**Recommendation:** 
- For audit logs: Use PostgreSQL with timescaledb, or cloud services like AWS CloudWatch, Datadog
- For user profiles: Use PostgreSQL or Redis for caching

This is an architectural change that requires significant refactoring.

---

### Issue 10: ML Model Simplicity
**Problem:** Simple LogisticRegression with 5 features

**Recommendation:**
- Add more features: device fingerprinting, geo-velocity, graph features (recipient transaction history)
- Use gradient boosting (XGBoost/LightGBM) or neural networks
- Implement model versioning with MLflow or similar
- Add A/B testing capability

---

## Summary of File Changes

| File | Changes |
|------|---------|
| config.py | Remove stale weight config values |
| decision_engine/engine.py | Fix floating point with round(), remove tolerance logic |
| layers/lm_layer.py | Update to new OpenAI client API |
| .gitignore | Add *.db, __pycache__, etc. |
| api/main.py | Fix double-counting bug, add security middleware |
| api/security.py (new) | Add API key and rate limiting |
| DECISION_LOGIC.md | Match threshold values with engine |
