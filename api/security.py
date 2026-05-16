import os
from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    if api_key != os.getenv("GATEWAY_API_KEY", "default-test-key"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
