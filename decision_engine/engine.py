import sys
import os
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from decision_engine.decision import Decision

class DecisionEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.allow_threshold = config.get('ALLOW_THRESHOLD', 0.3)
        self.verify_threshold = config.get('VERIFY_THRESHOLD', 0.55)
        
    def decide(self, transaction: Dict[str, Any], user: Dict[str, Any], rules_signal: Dict[str, Any], ml_signal: Dict[str, Any], lm_signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate signals and make a strict rule-based decision based on Base Risk.
        """
        # Rule Layer Overrides
        if rules_signal.get('action_override') == 'lock_account':
            return {
                'decision': Decision.LOCK_ACCOUNT,
                'combined_risk_score': 1.0,
                'required_actions': ['account_locked'],
                'reasoning': "Account locked due to severe rule violations.",
                'signals': {'rules': rules_signal, 'ml': ml_signal, 'lm': lm_signal}
            }

        # Calculate Combined Risk Score
        rules_risk = rules_signal.get('risk_score', 0.0)
        ml_risk = ml_signal.get('anomaly_score') # Might be None
        lm_risk_boost = lm_signal.get('risk_boost', 0.0)
        
        ml_unavailable = ml_risk is None
        base_risk = rules_risk if ml_unavailable else max(rules_risk, ml_risk)
        
        # Use the maximum of the individual risk scores plus the LLM boost.
        combined_risk = round(min(1.0, base_risk + lm_risk_boost), 2)
        
        ALLOW_CUTOFF = self.allow_threshold
        ESCALATE_CUTOFF = self.verify_threshold
        
        # Threshold logic without tolerance
        if combined_risk < ALLOW_CUTOFF:
            decision = Decision.ALLOW
            required_actions = []
            
        elif combined_risk > ESCALATE_CUTOFF:
            decision = Decision.ESCALATE_TO_HUMAN
            required_actions = ['human_review', 'phone_verification']
            
        else: # Verification region, including edge cases near boundaries
            decision = Decision.REQUIRE_VERIFICATION
            required_actions = self._get_verification_actions(transaction, user)
        
        # Uncertainty bias: if ML is down and rules are in an ambiguous range,
        # bias toward VERIFY rather than ALLOW. Uncertainty should increase friction.
        if ml_unavailable and decision == Decision.ALLOW and combined_risk >= (ALLOW_CUTOFF - 0.1):
            decision = Decision.REQUIRE_VERIFICATION
            required_actions = self._get_verification_actions(transaction, user)
            
        return {
            'decision': decision,
            'combined_risk_score': combined_risk,
            'required_actions': required_actions,
            'reasoning': self._generate_reasoning(combined_risk, rules_signal, ml_signal, lm_signal, decision.value),
            'signals': {
                'rules': rules_signal,
                'ml': ml_signal,
                'lm': lm_signal
            }
        }
        
    def _get_verification_actions(self, transaction: Dict[str, Any], user: Dict[str, Any]) -> List[str]:
        actions = ['user_verification']
        
        amount = transaction.get('amount', 0)
        if amount > 10000:
            actions.append('phone_verification')
            
        if transaction.get('destination_country') not in user.get('known_countries', []):
            actions.append('video_verification')
            
        # Simplistic international check
        if transaction.get('destination_country') != user.get('residence_country', transaction.get('destination_country', 'XX')):
            actions.append('email_verification')
            
        return actions

    def _generate_reasoning(self, combined_risk: float, rules_signal: Dict[str, Any], ml_signal: Dict[str, Any], lm_signal: Dict[str, Any], decision_str: str) -> str:
        ml_msg = ml_signal.get('explanation', 'No explanation')
        if ml_signal.get('unavailable'):
            ml_msg = "[UNAVAILABLE] Relying on rules only. " + ml_msg
            
        ml_score_str = f"{ml_signal.get('anomaly_score'):.2f}" if ml_signal.get('anomaly_score') is not None else "UNKNOWN"

        return f"""
Combined Risk Score: {combined_risk:.2f}

Rules Layer ({rules_signal.get('risk_score', 0):.2f}):
{rules_signal.get('explanation', 'No explanation')}

ML Layer ({ml_score_str}):
{ml_msg}

LLM Analysis (advisory, {lm_signal.get('risk_boost', 0):.2f} boost):
{lm_signal.get('explanation', 'No explanation')}

Decision: {decision_str}
"""
