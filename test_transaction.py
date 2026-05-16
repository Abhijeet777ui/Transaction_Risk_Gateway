import requests
import uuid
from datetime import datetime

# Configuration
URL = "http://127.0.0.1:8000/evaluate"
API_KEY = "gateway-dev-key-2024"  # From your .env file

def send_test_transaction():
    payload = {
        "transaction_id": str(uuid.uuid4()),
        "user_id": "user_999",
        "amount": 450.00,
        "currency": "GBP",
        "recipient_id": "recip_123",
        "recipient_name": "Electronics Store",
        "destination_country": "GB",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "notes": "Buying a new laptop"
    }
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    print(f"Sending transaction for {payload['amount']}...")
    
    try:
        response = requests.post(URL, json=payload, headers=headers)
        if response.status_code == 422:
            print("\nValidation Error (422):")
            print(response.json())
            return
        response.raise_for_status()
        result = response.json()
        
        print("\nResponse Received:")
        print(f"Decision: {result['decision'].upper()}")
        print(f"Risk Score: {result['combined_risk_score']}")
        print(f"Message: {result['user_message']}")
        print("\nNow check DataGrip! Refresh the 'audit_logs' table to see this entry.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    send_test_transaction()
