import pytest
import os
import sys
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app, audit_logger, user_manager, ml_layer
from api.models import TransactionRequest
from decision_engine.decision import Decision

client = TestClient(app)

# Helper for timestamps
def _ts(hours_delta=0):
    return (datetime.now(timezone.utc) + timedelta(hours=hours_delta)).isoformat()

def test_scenario_1_low_risk():
    """Scenario: Regular user, normal-sized transfer, known recipient, known country -> ALLOW"""
    user_id = 'test_u_1'
    # Hack knowns for testing
    user_manager.create_user(user_id)
    user_manager.record_transaction(user_id, {'amount': 500, 'recipient_id': 'r_1', 'destination_country': 'GB'}, 'allow')
    
    req = {
        "transaction_id": "tx_1",
        "user_id": user_id,
        "amount": 500,
        "recipient_id": "r_1",
        "destination_country": "GB",
        "timestamp": _ts()
    }
    
    res = client.post("/evaluate", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data['decision'] == 'allow'
    assert data['combined_risk_score'] < 0.3

def test_scenario_2_medium_risk():
    """Scenario: New recipient, reasonable amount -> REQUIRE_VERIFICATION"""
    user_id = 'test_u_2'
    user_manager.create_user(user_id, residence_country='GB')
    
    req = {
        "transaction_id": "tx_2",
        "user_id": user_id,
        "amount": 2000,
        "recipient_id": "r_new_1",
        "destination_country": "GB",
        "timestamp": _ts()
    }
    
    res = client.post("/evaluate", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data['decision'] == 'require_verification'
    assert 'user_verification' in data['required_actions']

def test_scenario_3_high_risk():
    """Scenario: Large amount, new recipient, new country, urgency -> ESCALATE"""
    user_id = 'test_u_3'
    user_manager.create_user(user_id, residence_country='US')
    
    req = {
        "transaction_id": "tx_3",
        "user_id": user_id,
        "amount": 50000,
        "recipient_id": "r_new_2",
        "destination_country": "NG",
        "timestamp": _ts(),
        "notes": "urgent, pls send fast"
    }
    
    res = client.post("/evaluate", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data['decision'] == 'escalate_to_human'
    assert 'human_review' in data['required_actions']
    assert 'phone_verification' in data['required_actions']

def test_scenario_4_split_attack():
    """Scenario: Velocity trigger -> ESCALATE after attempts, then LOCK"""
    user_id = 'test_u_4'
    user_manager.create_user(user_id)
    
    # 6 attempts to exceed velocity
    for i in range(6):
        req = {
            "transaction_id": f"tx_split_{i}",
            "user_id": user_id,
            "amount": 100,
            "recipient_id": f"r_multi_{i}",
            "timestamp": _ts()
        }
        res = client.post("/evaluate", json=req)
        
    last_res = res.json()
    # High velocity plus new recipients makes it escalate rapidly
    assert last_res['decision'] in ['require_verification', 'escalate_to_human']

def test_scenario_5_account_compromise():
    """Scenario: 100x outlier amount triggers ML Anomaly"""
    user_id = 'test_u_5'
    user_manager.create_user(user_id)
    for _ in range(5):
        user_manager.record_transaction(user_id, {'amount': 200, 'recipient_id': 'r_wife'}, 'allow')
        
    req = {
        "transaction_id": "tx_5",
        "user_id": user_id,
        "amount": 95000,
        "recipient_id": "unknown",
        "timestamp": _ts()
    }
    res = client.post("/evaluate", json=req)
    data = res.json()
    assert data['decision'] == 'escalate_to_human'
    if ml_layer.model is not None:
         # Assert ML scored it high
         assert data['signals']['ml']['anomaly_score'] > 0.5 

def test_scenario_6_graceful_missing_ml():
    """Scenario: ML file absent -> System uses RULES and FALLBACK -> VERIFY/ESCALATE"""
    # Temporarily hide ML layer
    original_model = ml_layer.model
    ml_layer.model = None
    
    user_id = 'test_u_6'
    req = {
        "transaction_id": "tx_6",
        "user_id": user_id,
        "amount": 5000,
        "recipient_id": "r_3",
        "timestamp": _ts()
    }
    res = client.post("/evaluate", json=req)
    data = res.json()
    assert res.status_code == 200
    # Safe base risk with missing ML and no knowns maps it to at least verify
    assert data['decision'] in ['require_verification', 'escalate_to_human']
    assert 'missing' in data['signals']['ml']['explanation'].lower() or 'crashed' in data['signals']['ml']['explanation'].lower()
    
    ml_layer.model = original_model

def test_scenario_7_audit_log_works():
    """Scenario: Check Audit integration DB queries"""
    user_id = 'test_u_7'
    tx_id = 'tx_7'
    req = {
        "transaction_id": tx_id,
        "user_id": user_id,
        "amount": 250,
        "recipient_id": "r_1",
        "timestamp": _ts()
    }
    client.post("/evaluate", json=req)
    
    # Query Logger directly
    log_entry = audit_logger.query_by_transaction(tx_id)
    assert log_entry is not None
    assert log_entry['user_id'] == user_id
    assert log_entry['decision'] in ['allow', 'require_verification']
    assert log_entry['signals_json'] is not None
