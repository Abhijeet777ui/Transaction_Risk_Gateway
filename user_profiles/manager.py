import sqlite3
import json
import os
from datetime import datetime, timezone
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from user_profiles.profile import UserProfile

class UserProfileManager:
    def __init__(self, db_path='users.db'):
        if db_path == ':memory:':
            self.db_path = db_path
        else:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(root_dir, db_path)
            
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                created_at DATETIME NOT NULL,
                residence_country TEXT DEFAULT 'XX',
                known_recipients TEXT NOT NULL,
                known_countries TEXT NOT NULL,
                transaction_history TEXT NOT NULL,
                failed_attempts_in_last_hour INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def get_user(self, user_id: str) -> dict:
        """Retrieves and constructs a UserProfile as a dictionary for the Engine"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            created_at = datetime.fromisoformat(row[1])
            profile = UserProfile(
                id=row[0],
                created_at=created_at,
                residence_country=row[2],
                known_recipients=json.loads(row[3]),
                known_countries=json.loads(row[4]),
                transaction_history=json.loads(row[5]),
                failed_attempts_in_last_hour=row[6]
            )
            return profile.to_dict()
        return None
        
    def create_user(self, user_id: str, residence_country: str = "XX") -> dict:
        """Creates a new user profile"""
        profile = UserProfile(
            id=user_id,
            created_at=datetime.utcnow(),
            residence_country=residence_country
        )
        self._save_profile(profile)
        return profile.to_dict()
        
    def _save_profile(self, profile: UserProfile):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (
                id, created_at, residence_country, known_recipients, 
                known_countries, transaction_history, failed_attempts_in_last_hour
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile.id,
            profile.created_at.isoformat(),
            profile.residence_country,
            json.dumps(profile.known_recipients),
            json.dumps(profile.known_countries),
            json.dumps(profile.transaction_history),
            profile.failed_attempts_in_last_hour
        ))
        
        conn.commit()
        conn.close()
        
    def record_transaction(self, user_id: str, transaction: dict, decision: str):
        """Update user behaviors and known lists based on outcome"""
        # We only record behavior as 'known' if the system explicitly allowed it
        user_dict = self.get_user(user_id)
        if not user_dict:
            return
            
        profile = UserProfile(
            id=user_id,
            created_at=datetime.fromisoformat(user_dict['created_at']),
            residence_country=user_dict['residence_country'],
            known_recipients=user_dict['known_recipients'],
            known_countries=user_dict['known_countries'],
            transaction_history=user_dict.get('transaction_history', []),
            failed_attempts_in_last_hour=user_dict.get('failed_attempts_in_last_hour', 0)
        )
            
        if decision == 'allow':
            recipient = transaction.get('recipient_id')
            country = transaction.get('destination_country')
            timestamp = transaction.get('timestamp')
            
            if recipient and recipient not in profile.known_recipients:
                profile.known_recipients.append(recipient)
                
            if country and country not in profile.known_countries:
                profile.known_countries.append(country)
                
            tx_record = {'amount': transaction.get('amount', 0)}
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    tx_record['hour'] = dt.hour
                except Exception:
                    pass
            
            profile.transaction_history.append(tx_record)
            
        # Reset failed attempts on a successful transaction that wasn't locked 
        if decision == 'allow':
             profile.failed_attempts_in_last_hour = 0
             
        self._save_profile(profile)
        
    def increment_failed_attempt(self, user_id: str):
         user_dict = self.get_user(user_id)
         if user_dict:
              user_dict['failed_attempts_in_last_hour'] += 1
              
              profile = UserProfile(
                    id=user_id,
                    created_at=datetime.fromisoformat(user_dict['created_at']),
                    residence_country=user_dict['residence_country'],
                    known_recipients=user_dict['known_recipients'],
                    known_countries=user_dict['known_countries'],
                    transaction_history=user_dict.get('transaction_history', []),
                    failed_attempts_in_last_hour=user_dict['failed_attempts_in_last_hour']
              )
              self._save_profile(profile)
