import json
import sqlite3
from datetime import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audit.schema import AuditLog

class AuditLogger:
    def __init__(self, db_path='audit.db'):
        # Just creating the database in the root of the project if it's a file
        if db_path == ':memory:':
            self.db_path = db_path
        else:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(root_dir, db_path)
        self._init_db()
    
    def _init_db(self):
        """Create audit table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                decision TEXT NOT NULL,
                combined_risk_score REAL NOT NULL,
                reasoning TEXT NOT NULL,
                signals_json TEXT NOT NULL,
                transaction_json TEXT NOT NULL,
                human_decision TEXT,
                reviewer_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON audit_logs(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_decision ON audit_logs(decision)')
        
        conn.commit()
        conn.close()
    
    def log(self, audit_entry: AuditLog):
        """Log a complete decision"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO audit_logs (
                    transaction_id, user_id, timestamp, decision,
                    combined_risk_score, reasoning, signals_json, transaction_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                audit_entry.transaction_id,
                audit_entry.user_id,
                audit_entry.timestamp,
                audit_entry.decision,
                audit_entry.combined_risk_score,
                audit_entry.reasoning,
                json.dumps(audit_entry.signals, default=str),
                json.dumps(audit_entry.transaction, default=str)
            ))
            
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
             print(f"Audit log entry for transaction {audit_entry.transaction_id} already exists.")
        except Exception as e:
            print(f"Audit logging error: {e}")
            raise
        finally:
            conn.close()
    
    def query_by_user(self, user_id, limit=100):
        """Get audit log for specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM audit_logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        
        # Convert tuples to list of dicts for easy reading
        names = [description[0] for description in cursor.description]
        results = [dict(zip(names, row)) for row in rows]
        conn.close()
        return results
    
    def query_by_transaction(self, transaction_id):
        """Get audit log for specific transaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM audit_logs
            WHERE transaction_id = ?
        ''', (transaction_id,))
        
        row = cursor.fetchone()
        
        if row:
            names = [description[0] for description in cursor.description]
            result = dict(zip(names, row))
        else:
            result = None
            
        conn.close()
        return result
