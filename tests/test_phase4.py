import pytest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layers.lm_layer import LMLayer

def test_llm_layer_missing_api_key_fallback():
    # If API key is missing, it should fall back safely without crashing
    layer = LMLayer(provider='openai', api_key=None)
    
    transaction = {'notes': 'urgent pls send fast'}
    user = {}
    signals = {}
    
    result = layer.evaluate(transaction, user, signals)
    
    assert result['risk_boost'] == 0.0
    assert 'warning' in result
    assert result['behavioral_flags'] == []

def test_llm_layer_no_notes_short_circuit():
    layer = LMLayer(provider='openai')
    
    transaction = {'amount': 500} # No notes
    user = {}
    
    result = layer.evaluate(transaction, user, {})
    
    assert result['risk_boost'] == 0.0
    assert 'No transaction notes' in result['explanation']
