import sys
sys.path.append('.')
from config import RULES, DECISION_ENGINE
from layers.rules_layer import RulesLayer
from decision_engine.engine import DecisionEngine
from datetime import datetime, timezone

rules_layer = RulesLayer(RULES)
engine = DecisionEngine(DECISION_ENGINE)
ts = datetime.now(timezone.utc).isoformat()

ml_down = {'anomaly_score': None, 'feature_importance': {}, 'explanation': 'ML crashed.', 'unavailable': True}
lm_low  = {'behavioral_flags': [], 'explanation': 'No notes.', 'risk_boost': 0.0}

# A: Mid-range rules (0.3), ML down => uncertainty bias => VERIFY
txn_a = {'amount': 1500, 'recipient_id': 'new_1', 'destination_country': 'GB', 'timestamp': ts}
user_a = {'known_recipients': ['known_1'], 'known_countries': ['GB']}
rules_a = rules_layer.evaluate(txn_a, user_a)
result_a = engine.decide(txn_a, user_a, rules_a, ml_down, lm_low)
expected_a = 'require_verification'
status_a = 'PASS' if result_a['decision'].value == expected_a else 'FAIL'
print(f"[ML DOWN] Mid Rules ({rules_a['risk_score']:.2f}) => {result_a['decision'].value} (expected {expected_a}) {status_a}")

# B: Zero rules, ML down => rules are confident zero risk => ALLOW
txn_b = {'amount': 100, 'recipient_id': 'known_1', 'destination_country': 'GB', 'timestamp': ts}
user_b = {'known_recipients': ['known_1'], 'known_countries': ['GB']}
rules_b = rules_layer.evaluate(txn_b, user_b)
result_b = engine.decide(txn_b, user_b, rules_b, ml_down, lm_low)
expected_b = 'allow'
status_b = 'PASS' if result_b['decision'].value == expected_b else 'FAIL'
print(f"[ML DOWN] Zero Rules ({rules_b['risk_score']:.2f}) => {result_b['decision'].value} (expected {expected_b}) {status_b}")

# C: High rules, ML down => should escalate
txn_c = {'amount': 50000, 'recipient_id': 'new_3', 'destination_country': 'NG', 'timestamp': ts}
user_c = {'known_recipients': ['known_1'], 'known_countries': ['GB']}
rules_c = rules_layer.evaluate(txn_c, user_c)
result_c = engine.decide(txn_c, user_c, rules_c, ml_down, lm_low)
expected_c = 'escalate_to_human'
status_c = 'PASS' if result_c['decision'].value == expected_c else 'FAIL'
print(f"[ML DOWN] High Rules ({rules_c['risk_score']:.2f}) => {result_c['decision'].value} (expected {expected_c}) {status_c}")

print()
print("--- Reasoning Audit (Scenario A) ---")
print(result_a['reasoning'])
