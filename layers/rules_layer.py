from datetime import datetime
from typing import Dict, Any

class RulesLayer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def evaluate(self, transaction: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Args:
            transaction: Dict with keys: amount, recipient_id, destination_country, timestamp, etc.
            user: Dict with keys: id, account_age, known_recipients, known_countries, transaction_history
        
        Returns:
            Dict containing risk_score, triggered_rules, and explanation.
        """
        risk_score = 0.0
        triggered_rules = []
        explanation_parts = []
        
        amount = transaction.get('amount', 0)
        
        # 1. Repeated Failed Attempts (Blocking rule)
        # Assuming transaction_history might have a 'failed_attempts_in_last_hour' or similar. 
        # Alternatively, user profile should track this.
        failed_count = user.get('failed_attempts_in_last_hour', 0)
        if failed_count >= self.config.get('ACCOUNT_LOCK_THRESHOLD', 3):
            # Special case, system locks account and stops processing.
            return {
                'risk_score': 1.0,
                'triggered_rules': [{'rule': 'account_locked', 'risk_added': 1.0}],
                'explanation': f"Account locked due to {failed_count} failed attempts in the last hour.",
                'action_override': 'lock_account'
            }
        elif failed_count >= 2:
            risk_score += 0.2
            triggered_rules.append({'rule': 'multiple_failures', 'risk_added': 0.2})
            explanation_parts.append("Multiple failed attempts detected recently.")

        # 2. Amount Threshold
        threshold_high = self.config.get('AMOUNT_THRESHOLD_HIGH', 10000)
        threshold_medium = self.config.get('AMOUNT_THRESHOLD_MEDIUM', 5000)
        if amount > threshold_high:
            risk_score += 0.3
            triggered_rules.append({'rule': 'amount_high', 'risk_added': 0.3})
            explanation_parts.append(f"Amount exceeds high threshold ({threshold_high}).")
        elif amount > threshold_medium:
            risk_score += 0.15
            triggered_rules.append({'rule': 'amount_medium', 'risk_added': 0.15})
            explanation_parts.append(f"Amount exceeds medium threshold ({threshold_medium}).")
            
        # 3. New Recipient
        recipient_id = transaction.get('recipient_id')
        if recipient_id not in user.get('known_recipients', []):
            risk_added = self.config.get('NEW_RECIPIENT_RISK', 0.3)
            risk_score += risk_added
            triggered_rules.append({'rule': 'new_recipient', 'risk_added': risk_added})
            explanation_parts.append("New recipient not in user's history.")
            
        # 4. New Country
        destination_country = transaction.get('destination_country')
        if destination_country not in user.get('known_countries', []):
            risk_added = self.config.get('NEW_COUNTRY_RISK', 0.2)
            risk_score += risk_added
            triggered_rules.append({'rule': 'new_country', 'risk_added': risk_added})
            explanation_parts.append("Destination country not in user's known countries.")
            
        # 5. Velocity Check
        txs_last_hour = user.get('transactions_in_last_hour', 0)
        max_vel = self.config.get('VELOCITY_MAX_PER_HOUR', 5)
        if txs_last_hour > max_vel:
            risk_score += 0.2
            triggered_rules.append({'rule': 'high_velocity', 'risk_added': 0.2})
            explanation_parts.append("Transaction velocity exceeds normal limits.")
            
        # 6. Account Age
        account_age_days = user.get('account_age', 365) # fallback to old
        min_age = self.config.get('MINIMUM_ACCOUNT_AGE_DAYS', 7)
        if account_age_days < min_age:
            risk_score += 0.25
            triggered_rules.append({'rule': 'new_account', 'risk_added': 0.25})
            explanation_parts.append("Account is very new.")
            
        # 7. Time-of-Day Anomaly
        try:
            timestamp_str = transaction.get('timestamp')
            if timestamp_str:
                tx_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                current_hour = tx_time.hour
                user_typical_hours = user.get('typical_transaction_hours', list(range(24))) # default any hour is typical
                
                if current_hour not in user_typical_hours and (current_hour in [22, 23, 0, 1, 2, 3, 4]):
                    risk_score += 0.1
                    triggered_rules.append({'rule': 'unusual_time', 'risk_added': 0.1})
                    explanation_parts.append("Transaction occurring at an unusual late-night hour.")
        except Exception:
            # Silently fail time parsing for the rule, default safe fallback
            pass

        return {
            'risk_score': min(risk_score, 1.0),
            'triggered_rules': triggered_rules,
            'explanation': " ".join(explanation_parts) if explanation_parts else "No high-risk deterministic rules triggered."
        }
