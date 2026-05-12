"""Smoke test: Gemini API connectivity using new google-genai SDK."""
import os, sys

env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, val = line.partition('=')
                os.environ.setdefault(key.strip(), val.strip())

api_key = os.getenv('GEMINI_API_KEY')
print(f"Key found: {api_key[:8]}...{api_key[-4:]}")

from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)

print("Calling gemini-flash-latest...")
response = client.models.generate_content(
    model="gemini-flash-latest",
    contents='Reply with only this JSON, no markdown: {"status": "ok", "message": "Gemini is working"}',
    config=types.GenerateContentConfig(
        temperature=0.3,
        max_output_tokens=100,
    )
)
print("Response:", response.text.strip())
print("\nSUCCESS: Gemini is connected and working!")
