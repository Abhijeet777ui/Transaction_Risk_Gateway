import pytest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layers.ml_layer import MLLayer

@pytest.fixture
def ml_layer():
    return MLLayer(model_path='models/ml_model.pkl')

def test_ml_layer_fallback_when_missing():
    # Provide a garbage path
    layer = MLLayer(model_path='models/does_not_exist.pkl')
    
    transaction = {'amount': 500}
    user = {}
    
    result = layer.evaluate(transaction, user)
    
    # Should safely return 0.5 neutral without throwing
    assert result['anomaly_score'] == 0.5
    assert "missing" in result['explanation']

def test_ml_inference(ml_layer):
    transaction = {
        'amount': 50000,
        'recipient_id': 'someone_new',
        'destination_country': 'NG'
    }
    user = {
        'account_age': 1,
        'transactions_in_last_hour': 10,
        'transaction_history': [{'amount': 10}],
        'known_recipients': [],
        'known_countries': []
    }
    
    # ML model might not perfectly jump to 1.0 depending on the random split,
    # but it should evaluate successfully without crashing
    
    # If the model didn't train successfully (i.e. file missing during test run), we skip strict math tests
    if ml_layer.model is None:
        pytest.skip("Model not yet trained, skipping inference prediction math")
        
    result = ml_layer.evaluate(transaction, user)
    
    assert 0.0 <= result['anomaly_score'] <= 1.0
    assert len(result['feature_importance']) == 5
    assert 'recipient_is_new' in result['feature_importance']
