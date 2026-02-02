#!/usr/bin/env python3
"""
Generate a dummy JWT token for testing the Enterprise AI Gateway
"""
from datetime import datetime, timedelta, timezone
from jose import jwt
import json

# Secret key (same as in settings.py default)
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
EXPIRATION_HOURS = 24

# Create token payload
payload = {
    "sub": "advisor@wealth.com",
    "lob": "wealth",
    "models": ["openai/gpt-4.1", "openai/gpt-4o-2024-11-20"],
    "groups": ["free", "pro", "enterprise"],
    "roles": ["user", "admin"],
    "rate_limit": 100,
    "iat": int(datetime.now(timezone.utc).timestamp()),
    "exp": int((datetime.now(timezone.utc) + timedelta(hours=EXPIRATION_HOURS)).timestamp())
}

# Create token
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

print("=" * 80)
print("🔐 DUMMY JWT TOKEN FOR TESTING")
print("=" * 80)
print(f"\nToken:\n{token}\n")

print("Token Payload:")
print(json.dumps(payload, indent=2))

print("\n" + "=" * 80)
print("📝 HOW TO USE THIS TOKEN:")
print("=" * 80)

print("\n1. In curl command:")
print(f"""
curl -X POST http://localhost:8000/gateway/prompt \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "prompt": "What is machine learning?",
    "model": "gpt-4"
  }}'
""")

print("\n2. In Python requests:")
print(f"""
import requests

headers = {{
    'Authorization': 'Bearer {token}',
    'Content-Type': 'application/json'
}}

data = {{
    'prompt': 'What is machine learning?',
    'model': 'gpt-4'
}}

response = requests.post('http://localhost:8000/gateway/prompt', headers=headers, json=data)
print(response.json())
""")

print("\n3. In Swagger UI (http://localhost:8000/docs):")
print(f"   Click 'Authorize' and paste: {token}")

print("\n" + "=" * 80)
