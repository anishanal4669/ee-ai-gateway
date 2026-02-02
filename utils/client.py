"""
Simple Python client for calling the Enterprise AI Gateway endpoints
"""

import requests
import json
from datetime import datetime, timedelta, timezone
from jose import jwt

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"


def generate_token(user_id="advisor@wealth.com", lob="wealth", 
                   models=None, permissions=None, rate_limit=100):
    """Generate a test JWT token"""
    if models is None:
        models = ["openai/gpt-4.1", "openai/gpt-4o-2024-11-20"]
    if permissions is None:
        permissions = ["read:prompt", "write:response"]
    
    payload = {
        "sub": user_id,
        "lob": lob,
        "models": models,
        "permissions": permissions,
        "rate_limit": rate_limit,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp())
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def call_health_check():
    """Call the health check endpoint"""
    print("\n" + "="*80)
    print("1. HEALTH CHECK ENDPOINT")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/health")
    data = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    return response.status_code == 200


def call_chat_completion(token, model="openai/gpt-4.1", prompt="What is AI?", api_key=None):
    """Call the chat completion endpoint"""
    print("\n" + "="*80)
    print("2. CHAT COMPLETION ENDPOINT")
    print("="*80)
    print(f"Model: {model}")
    print(f"Prompt: {prompt}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Add OpenAI API key if provided
    if api_key:
        headers["OPENAI_API_KEY"] = api_key
    
    payload = {
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "model": model,
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=headers,
        json=payload
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def call_rate_limit(token):
    """Get rate limit status"""
    print("\n" + "="*80)
    print("3. RATE LIMIT STATUS ENDPOINT")
    print("="*80)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        f"{BASE_URL}/rate-limit",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def main():
    """Main function"""
    import os
    
    print("\n" + "="*80)
    print("ENTERPRISE AI GATEWAY - PYTHON CLIENT")
    print("="*80)
    
    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  WARNING: OPENAI_API_KEY not set in environment")
        print("Set it with: export OPENAI_API_KEY='your-key'")
    else:
        print(f"✓ OPENAI_API_KEY found")
    
    # Step 1: Generate token
    print("\nGenerating JWT token...")
    token = generate_token()
    print(f"Token: {token[:50]}...")
    
    # Step 2: Call health check
    call_health_check()
    
    # Step 3: Call rate limit status
    call_rate_limit(token)
    
    # Step 4: Call chat completions with gpt-4 (now passing api_key)
    call_chat_completion(token, model="openai/gpt-4.1", prompt="What is machine learning?", api_key=api_key)

    # Step 5: Call chat completions with gpt-4o-2024-11-20
    call_chat_completion(token, model="openai/gpt-4o-2024-11-20", prompt="Explain quantum computing", api_key=api_key)

    # Step 6: Multi-turn conversation
    print("\n" + "="*80)
    print("4. MULTI-TURN CONVERSATION")
    print("="*80)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Add OpenAI API key if provided
    if api_key:
        headers["OPENAI_API_KEY"] = api_key
    
    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! How are you?"},
            {"role": "assistant", "content": "I'm doing great, thank you!"},
            {"role": "user", "content": "What can you help me with?"}
        ],
        "model": "openai/gpt-4.1",
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=headers,
        json=payload
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to server")
        print("Make sure the server is running: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {e}")
