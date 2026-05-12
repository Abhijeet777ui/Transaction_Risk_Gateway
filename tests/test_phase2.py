import pytest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from user_profiles.manager import UserProfileManager
from user_profiles.profile import UserProfile

@pytest.fixture
def profile_manager():
    # Use a specific temp DB for profiles testing
    db_name = 'test_users.db'
    manager = UserProfileManager(db_name)
    yield manager
    
    import time
    time.sleep(0.1)
    if os.path.exists(manager.db_path):
        try:
            os.remove(manager.db_path)
        except PermissionError:
            pass

def test_user_creation_and_retrieval(profile_manager):
    user_id = 'test_user_001'
    created = profile_manager.create_user(user_id, residence_country='US')
    
    assert created['id'] == user_id
    assert created['residence_country'] == 'US'
    assert created['failed_attempts_in_last_hour'] == 0
    assert len(created['known_recipients']) == 0
    
    retrieved = profile_manager.get_user(user_id)
    assert retrieved is not None
    assert retrieved['id'] == user_id

def test_record_transaction_learning(profile_manager):
    user_id = 'test_user_002'
    profile_manager.create_user(user_id)
    
    transaction = {
        'amount': 500,
        'recipient_id': 'new_friend',
        'destination_country': 'FR',
        'timestamp': '2026-04-23T14:00:00Z'
    }
    
    # Simulate an allowed transaction
    profile_manager.record_transaction(user_id, transaction, 'allow')
    
    retrieved = profile_manager.get_user(user_id)
    assert 'new_friend' in retrieved['known_recipients']
    assert 'FR' in retrieved['known_countries']
    assert len(retrieved['transaction_history']) == 1
    assert retrieved['transaction_history'][0]['amount'] == 500
    assert 14 in retrieved['typical_transaction_hours']

def test_failed_attempts_increment(profile_manager):
    user_id = 'test_user_003'
    profile_manager.create_user(user_id)
    
    profile_manager.increment_failed_attempt(user_id)
    profile_manager.increment_failed_attempt(user_id)
    
    retrieved = profile_manager.get_user(user_id)
    assert retrieved['failed_attempts_in_last_hour'] == 2
    
    # An allowed transaction should reset it
    profile_manager.record_transaction(user_id, {}, 'allow')
    
    retrieved_after = profile_manager.get_user(user_id)
    assert retrieved_after['failed_attempts_in_last_hour'] == 0
