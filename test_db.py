"""Smoke test: PostgreSQL connectivity."""
import os
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, val = line.partition('=')
                os.environ.setdefault(key.strip(), val.strip())

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Testing connection to: {DATABASE_URL}")

async def test_connection():
    try:
        engine = create_async_engine(DATABASE_URL)
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"\nSUCCESS: Connected to {version}")
    except Exception as e:
        print(f"\nERROR: Could not connect to database.\n{e}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. You created the 'gateway' database: CREATE DATABASE gateway;")
        print("3. You updated yourpassword in the .env file")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_connection())
