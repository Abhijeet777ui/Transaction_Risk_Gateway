from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class AuditLog:
    """Complete record of a single decision"""
    
    # Request info
    transaction_id: str
    user_id: str
    timestamp: datetime
    
    # Transaction details
    transaction: Dict[str, Any]
    
    # All signals
    signals: Dict[str, Any]
    
    # Decision
    decision: str  # ALLOW, REQUIRE_VERIFICATION, ESCALATE_TO_HUMAN, LOCK_ACCOUNT
    combined_risk_score: float
    required_actions: List[str]
    reasoning: str
    
    # Outcome
    user_action: Optional[str] = None  # approved, denied, appealed
    human_reviewer_id: Optional[str] = None
    human_decision: Optional[str] = None
    appeal_status: Optional[str] = None
    
    # Metadata
    system_version: str = "1.0.0"
    environment: str = "production"
