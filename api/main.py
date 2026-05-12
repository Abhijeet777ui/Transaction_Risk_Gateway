from fastapi import FastAPI, HTTPException, Depends, Request
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RULES, DECISION_ENGINE, LLM, AUDIT, validate_config
validate_config()

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from api.security import limiter, verify_api_key

from layers.rules_layer import RulesLayer
from layers.ml_layer import MLLayer
from layers.lm_layer import LMLayer
from decision_engine.engine import DecisionEngine
from decision_engine.decision import Decision

from audit.schema import AuditLog
from audit.pg_logger import PGAuditLogger
from user_profiles.pg_manager import PGUserProfileManager

from database.connection import init_db, AsyncSessionLocal
from api.models import TransactionRequest, TransactionResponse

app = FastAPI(title="Explainable Transaction Risk Gateway")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

metrics = {
    "total_requests": 0,
    "allows": 0,
    "verifies": 0,
    "escalates": 0,
    "errors": 0,
    "fallbacks": {
        "ml": 0,
        "llm": 0,
        "db": 0
    }
}

# Initialize stateless core layers (no DB needed at construction time)
rules_layer = RulesLayer(RULES)
ml_layer = MLLayer('models/ml_model.pkl')
lm_layer = LMLayer(LLM.get('PROVIDER', 'openai'))
decision_engine = DecisionEngine(DECISION_ENGINE)

# PostgreSQL-backed managers (stateless — session passed per-request)
audit_logger = PGAuditLogger()
user_manager = PGUserProfileManager()


@app.on_event("startup")
async def startup():
    """Create all tables on first run (idempotent)."""
    await init_db()


@app.get("/metrics")
def get_metrics():
    return metrics


@app.get("/health")
async def health():
    """Simple liveness probe."""
    return {"status": "ok"}


@app.post("/evaluate", response_model=TransactionResponse)
@limiter.limit("100/minute")
async def evaluate_transaction(req: Request, request: TransactionRequest, api_key: str = Depends(verify_api_key)):
    metrics["total_requests"] += 1

    async with AsyncSessionLocal() as session:
        try:
            # Validate critical inputs
            if request.amount <= 0:
                raise HTTPException(status_code=400, detail="Amount must be positive")

            # Get or create user profile
            user_dict = await user_manager.get_user(session, request.user_id)
            if not user_dict:
                user_dict = await user_manager.create_user(session, request.user_id)

            # Build transaction dictionary
            transaction = request.model_dump()

            # --- EXECUTE LAYERS ---
            rules_signal = rules_layer.evaluate(transaction, user_dict)
            ml_signal = ml_layer.evaluate(transaction, user_dict)
            lm_signal = await lm_layer.evaluate_async(transaction, user_dict, {'rules': rules_signal, 'ml': ml_signal})

            # --- MAKE DECISION ---
            decision_result = decision_engine.decide(
                transaction, user_dict, rules_signal, ml_signal, lm_signal
            )

            decision_str = decision_result['decision'].value

            # --- METRICS & FALLBACK TRACKING ---
            fallbacks_used = {
                "ml_unavailable": ml_signal.get('unavailable', False),
                "llm_timeout": (
                    lm_signal.get('risk_boost', -1) == 0.0
                    and lm_signal.get('behavioral_flags') == []
                    and 'unavailable' in lm_signal.get('explanation', '')
                ),
                "db_fallback": False
            }

            if fallbacks_used["ml_unavailable"]: metrics["fallbacks"]["ml"] += 1
            if fallbacks_used["llm_timeout"]:    metrics["fallbacks"]["llm"] += 1

            if decision_str == 'allow':
                metrics["allows"] += 1
            elif decision_str == 'require_verification':
                metrics["verifies"] += 1
            elif decision_str == 'escalate_to_human':
                metrics["escalates"] += 1

            # --- AUDIT LOGGING ---
            try:
                ts = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                ts = datetime.utcnow()

            audit_entry = AuditLog(
                transaction_id=request.transaction_id,
                user_id=request.user_id,
                timestamp=ts,
                transaction=transaction,
                signals={'rules': rules_signal, 'ml': ml_signal, 'lm': lm_signal, 'fallbacks_used': fallbacks_used},
                decision=decision_str,
                combined_risk_score=decision_result['combined_risk_score'],
                required_actions=decision_result['required_actions'],
                reasoning=decision_result['reasoning'],
            )
            await audit_logger.log(session, audit_entry)

            # --- PROFILE UPDATES ---
            if decision_str != 'lock_account':
                await user_manager.record_transaction(session, request.user_id, transaction, decision_str)

            # Session commits automatically on exit via get_db context (explicit here)
            await session.commit()

            # --- CONSTRUCT FINAL OUTPUT ---
            if decision_str == 'allow':
                user_message = "Transaction approved."
            elif decision_str == 'require_verification':
                user_message = f"Transaction requires verification. Please complete: {', '.join(decision_result['required_actions'])}"
            elif decision_str == 'lock_account':
                user_message = "Account locked due to severe risk violations or multiple failures."
            else:
                user_message = "This transaction requires manual review. We'll contact you at the phone number on file within 5 minutes."

            return TransactionResponse(
                decision=decision_str,
                combined_risk_score=decision_result['combined_risk_score'],
                required_actions=decision_result['required_actions'],
                signals=decision_result['signals'],
                user_message=user_message,
                appeal_available=(decision_str in ['require_verification', 'escalate_to_human', 'lock_account']),
                appeal_method="Call support or verify via 2FA"
            )

        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            print(f"CRITICAL ERROR in evaluate_transaction: {e}")
            metrics["errors"] += 1
            metrics["fallbacks"]["db"] += 1

            return TransactionResponse(
                decision=Decision.ESCALATE_TO_HUMAN.value,
                combined_risk_score=1.0,
                required_actions=['human_review', 'phone_verification'],
                signals={"fallbacks_used": {"ml_unavailable": False, "llm_timeout": False, "db_fallback": True}},
                user_message="Our system encountered an error. We have escalated this transaction for immediate manual review.",
                appeal_available=True,
                appeal_method="Call support immediately"
            )
