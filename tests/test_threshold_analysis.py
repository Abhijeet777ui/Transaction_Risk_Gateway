import sys
import os
import json
from datetime import datetime, timezone
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RULES, DECISION_ENGINE, LLM
from layers.rules_layer import RulesLayer
from layers.ml_layer import MLLayer
from layers.lm_layer import LMLayer
from decision_engine.engine import DecisionEngine

def analyze_thresholds():
    """
    Run the threshold analysis to see exactly how the scoring math evaluates.
    """
    rules_layer = RulesLayer(RULES)
    ml_layer = MLLayer('models/ml_model.pkl')
    lm_layer = LMLayer(LLM.get('PROVIDER', 'openai'))
    decision_engine = DecisionEngine(DECISION_ENGINE)
    
    test_scenarios = [
        {
            "name": "Low Risk",
            "input": {"amount": 500, "recipient_id": "known_1", "destination_country": "GB", "timestamp": datetime.now(timezone.utc).isoformat()},
            "user": {"known_recipients": ["known_1"], "known_countries": ["GB"]},
            "expected": "allow"
        },
        {
            "name": "Medium Risk",
            "input": {"amount": 5000, "recipient_id": "new_1", "destination_country": "GB", "timestamp": datetime.now(timezone.utc).isoformat()},
            "user": {"known_recipients": ["known_1"], "known_countries": ["GB"]},
            "expected": "require_verification"
        },
        {
            "name": "High Risk Boundaries",
            "input": {"amount": 10000, "recipient_id": "new_2", "destination_country": "NG", "timestamp": datetime.now(timezone.utc).isoformat()},
            "user": {"known_recipients": ["known_1"], "known_countries": ["GB"]},
            "expected": "escalate_to_human" # Or verify? Let's check where it lands
        },
        {
            "name": "Extremely High Risk",
            "input": {"amount": 50000, "recipient_id": "new_3", "destination_country": "NG", "notes": "urgent pls send fast", "timestamp": datetime.now(timezone.utc).isoformat()},
            "user": {"known_recipients": ["known_1"], "known_countries": ["GB"]},
            "expected": "escalate_to_human"
        }
    ]
    
    for scenario in test_scenarios:
        transaction = scenario['input']
        user = scenario['user']
        
        rules_signal = rules_layer.evaluate(transaction, user)
        ml_signal = ml_layer.evaluate(transaction, user)
        lm_signal = lm_layer.evaluate(transaction, user, {'rules': rules_signal, 'ml': ml_signal})
        
        result = decision_engine.decide(transaction, user, rules_signal, ml_signal, lm_signal)
        
        print(f"\n{scenario['name']}:")
        print(f"  Rules Score: {rules_signal.get('risk_score', 0):.2f}")
        print(f"  ML Score:    {ml_signal.get('anomaly_score', 0):.2f}")
        print(f"  LM Boost:    {lm_signal.get('risk_boost', 0):.2f}")
        print(f"  Combined:    {result['combined_risk_score']:.2f}")
        print(f"  Decision:    {result['decision'].value}")
        print(f"  Expected:    {scenario['expected']}")
        print(f"  Status:      {'PASS' if result['decision'].value == scenario['expected'] else 'FAIL'}")

if __name__ == "__main__":
    analyze_thresholds()
