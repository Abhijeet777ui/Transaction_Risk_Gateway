from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime

@dataclass
class UserProfile:
    """Represents the historical state of a user for decision signaling"""
    id: str
    created_at: datetime
    residence_country: str = "XX"
    known_recipients: List[str] = field(default_factory=list)
    known_countries: List[str] = field(default_factory=list)
    
    # Simple history list of dicts to extract percentiles/averages easily
    # e.g. [{"amount": 500, "hour": 14, "timestamp": "..."}]
    transaction_history: List[Dict[str, Any]] = field(default_factory=list)
    
    failed_attempts_in_last_hour: int = 0
    
    @property
    def account_age(self) -> int:
        """Returns account age in days"""
        return max((datetime.utcnow() - self.created_at).days, 0)
        
    @property
    def typical_transaction_hours(self) -> List[int]:
        """Extract hours from transaction history"""
        # In a real app this would find statistical modes. Here we just return unique seen hours
        return list({tx['hour'] for tx in self.transaction_history if 'hour' in tx})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict structure required by Layers"""
        return {
            'id': self.id,
            'account_age': self.account_age,
            'created_at': self.created_at.isoformat(),
            'known_recipients': self.known_recipients,
            'known_countries': self.known_countries,
            'residence_country': self.residence_country,
            'typical_transaction_hours': self.typical_transaction_hours,
            'failed_attempts_in_last_hour': self.failed_attempts_in_last_hour,
            'transaction_history': self.transaction_history
        }
