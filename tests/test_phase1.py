import sys
import os
import pytest
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RULES, DECISION_ENGINE
from layers.rules_layer import RulesLayer
from decision_engine.engine import DecisionEngine
from decision_engine.decision import Decision
from audit.schema import AuditLog
from audit.logger import AuditLogger

@pytest.fixture
def rules_layer():
    return RulesLayer(RULES)

@pytest.fixture
def decision_engine():
    return DecisionEngine(DECISION_ENGINE)

@pytest.fixture
def audit_logger():
    # Use a temp file for SQLite testing so connections share data
    db_name = 'test_audit.db'
    logger = AuditLogger(db_name)
    yield logger
    
    # Cleanup after test
    import time
    time.sleep(0.1) # Small delay to ensure file handles are released
    if os.path.exists(logger.db_path):
        try:
            os.remove(logger.db_path)
        except PermissionError:
            pass

def test_low_risk_scenario(rules_layer, decision_engine, audit_logger):
    transaction = {
        'transaction_id': 'txn_low_001',
        'amount': 500,
        'recipient_id': 'known_recipient_1',
        'destination_country': 'GB',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    user = {
        'id': 'user_123',
        'account_age': 365,
        'known_recipients': ['known_recipient_1'],
        'known_countries': ['GB'],
        'residence_country': 'GB'
    }
    
    # 1. Rule Layer Evaluation
    rules_signal = rules_layer.evaluate(transaction, user)
    assert rules_signal['risk_score'] == 0.0
    
    # 2. Decision Engine Evaluation
    # Note: mocking ML and LLM signals as neutral for Phase 1 testing
    ml_signal = {'anomaly_score': 0.1, 'explanation': 'Normal'}
    lm_signal = {'risk_boost': 0.0, 'explanation': 'Normal'}
    
    decision_result = decision_engine.decide(transaction, user, rules_signal, ml_signal, lm_signal)
    
    assert decision_result['decision'] == Decision.ALLOW
    assert decision_result['combined_risk_score'] < 0.3
    
    # 3. Audit Logging
    audit_entry = AuditLog(
        transaction_id=transaction['transaction_id'],
        user_id=user['id'],
        timestamp=datetime.now(timezone.utc),
        transaction=transaction,
        signals={'rules': rules_signal, 'ml': ml_signal, 'lm': lm_signal},
        decision=decision_result['decision'].value,
        combined_risk_score=decision_result['combined_risk_score'],
        required_actions=decision_result['required_actions'],
        reasoning=decision_result['reasoning']
    )
    
    log_id = audit_logger.log(audit_entry)
    assert log_id > 0
    
    fetched = audit_logger.query_by_transaction(transaction['transaction_id'])
    assert fetched['decision'] == 'allow'

def test_account_lockout_rule_terminates(rules_layer, decision_engine):
    transaction = {
        'transaction_id': 'txn_lock_001',
        'amount': 500,
        'recipient_id': 'someone',
    }
    user = {
        'failed_attempts_in_last_hour': 3 # Triggers lockout
    }
    
    rules_signal = rules_layer.evaluate(transaction, user)
    assert rules_signal['action_override'] == 'lock_account'
    
    decision_result = decision_engine.decide(transaction, user, rules_signal, {}, {})
    assert decision_result['decision'] == Decision.LOCK_ACCOUNT

def test_missing_ml_graceful_routing(rules_layer, decision_engine):
    transaction = {
        'transaction_id': 'txn_miss_001',
        'amount': 5000,
        'recipient_id': 'someone',
    }
    user = {'failed_attempts_in_last_hour': 0}
    rules_signal = rules_layer.evaluate(transaction, user)
    
    # Passing empty ml_signal
    ml_signal = {}
    
    decision_result = decision_engine.decide(transaction, user, rules_signal, ml_signal, {})
    assert decision_result['decision'] == Decision.REQUIRE_VERIFICATION
    assert 'user_verification' in decision_result['required_actions']
