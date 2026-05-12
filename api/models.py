from pydantic import BaseModel
from typing import Dict, Any, List

class TransactionRequest(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    currency: str = "GBP"
    recipient_id: str
    recipient_name: str = ""
    destination_country: str = "XX"
    source_location: str = ""
    source_ip: str = ""
    timestamp: str  # ISO format requested
    notes: str = ""

class TransactionResponse(BaseModel):
    decision: str
    combined_risk_score: float
    required_actions: List[str]
    signals: Dict[str, Any]
    user_message: str
    appeal_available: bool
    appeal_method: str
