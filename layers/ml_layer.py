import pickle
import os
import numpy as np
from typing import Dict, Any

class MLLayer:
    def __init__(self, model_path: str = 'models/ml_model.pkl'):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.full_path = os.path.join(root_dir, model_path)
        self.model = self._load_model()
        
        # Define features so we can spit out meaningful importance easily
        self.feature_names = [
            'amount_zscore', 
            'recipient_is_new', 
            'country_is_new', 
            'velocity', 
            'account_age_days'
        ]

    def _load_model(self):
        if not os.path.exists(self.full_path):
            print(f"Warning: ML model not found at {self.full_path}")
            return None
        with open(self.full_path, 'rb') as f:
            return pickle.load(f)
            
    def _engineer_features(self, transaction: Dict[str, Any], user: Dict[str, Any]) -> list:
        # Amount Z-score (mocked based roughly on historical median if exact stats missing)
        amount = transaction.get('amount', 0)
        history = user.get('transaction_history', [])
        history_amounts = [t.get('amount', 0) for t in history] if history else []
        avg_amount = np.mean(history_amounts) if history_amounts else amount
        std_amount = np.std(history_amounts) if len(history_amounts) > 1 else max(amount * 0.1, 1)
        zscore = (amount - avg_amount) / std_amount if std_amount > 0 else 0
        
        # New Recipient
        recipient_new = 1.0 if transaction.get('recipient_id') not in user.get('known_recipients', []) else 0.0
        
        # New Country
        country_new = 1.0 if transaction.get('destination_country') not in user.get('known_countries', []) else 0.0
        
        # Velocity
        velocity = float(user.get('transactions_in_last_hour', 0))
        
        # Age
        age = float(user.get('account_age', 0))
        
        return [zscore, recipient_new, country_new, velocity, age]

    def evaluate(self, transaction: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate transaction using LR model, strictly bounded and falling back safely.
        """
        if self.model is None:
             return {
                 'anomaly_score': None,
                 'feature_importance': {},
                 'explanation': "ML model completely missing, returning neutral signal",
                 'unavailable': True
             }
             
        try:
             features = self._engineer_features(transaction, user)
             X = np.array([features])
             
             # Predict probability of class 1 (anomaly)
             probability = self.model.predict_proba(X)[0][1]
             
             # Brutally simple feature importance mock: input feature value * model coefficient weight
             contributions = X[0] * self.model.coef_[0]
             
             feature_importance = {name: float(val) for name, val in zip(self.feature_names, contributions)}
             
             # Highest contributor string
             top_feature = max(feature_importance.items(), key=lambda x: x[1])[0] if feature_importance else "unknown"
             
             return {
                 'anomaly_score': probability,
                 'feature_importance': feature_importance,
                 'explanation': f"Calculated anomaly score of {probability:.2f}. Primary risk driver: {top_feature}"
             }
             
        except Exception as e:
             # Fails gracefully without throwing downstream exception
             return {
                 'anomaly_score': None,
                 'feature_importance': {},
                 'explanation': f"ML evaluation crashed ({e}), returning safe neutral signal",
                 'unavailable': True
             }
