#!/bin/bash
# Setup script for Enterprise AI Gateway - Check and configure everything

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║           Enterprise AI Gateway - Setup Verification                      ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "This script will verify your setup and prepare you for testing."
echo ""

# Step 1: Check server
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Checking server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "✅ Server is running at http://localhost:8000"
else
    echo "❌ Server is NOT running"
    echo ""
    echo "To start the server, run:"
    echo "  cd enterprise-ai-gateway-mini"
    echo "  uvicorn app.main:app --reload"
    echo ""
    exit 1
fi

# Step 2: Check Redis
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Checking Redis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
else
    echo "⚠️  Redis might not be running"
    echo "To start Redis, run: redis-server"
    echo ""
fi

# Step 3: Check OpenAI API Key
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: OpenAI API Key Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY is not set in environment"
    echo ""
    echo "How to set it:"
    echo ""
    echo "Option 1: Set for current session"
    echo "  export OPENAI_API_KEY='sk-proj-...'"
    echo ""
    echo "Option 2: Set permanently (add to ~/.zshrc)"
    echo "  echo 'export OPENAI_API_KEY=\"sk-proj-...\"' >> ~/.zshrc"
    echo "  source ~/.zshrc"
    echo ""
    echo "Option 3: Get from .env file"
    echo "  source .env && echo \$OPENAI_API_KEY"
    echo ""
else
    echo "✅ OPENAI_API_KEY is set"
    echo "   Key preview: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -10}"
fi

# Step 4: Generate JWT Token
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Generate JWT Token"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v python3 &> /dev/null; then
    echo "Generating JWT token..."
    TOKEN=$(python3 -c "
import json
from datetime import datetime, timedelta, timezone
from jose import jwt

payload = {
    'sub': 'advisor@wealth.com',
    'lob': 'wealth',
    'models': ['openai/gpt-4.1', 'openai/gpt-3.5-turbo'],
    'permissions': ['read:prompt', 'write:response'],
    'rate_limit': 100,
    'iat': int(datetime.now(timezone.utc).timestamp()),
    'exp': int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp())
}

token = jwt.encode(payload, 'your-secret-key-change-in-production', algorithm='HS256')
print(token)
" 2>/dev/null)
    
    if [ ! -z "$TOKEN" ]; then
        echo "✅ JWT token generated successfully"
        echo ""
        echo "Token preview: ${TOKEN:0:20}...${TOKEN: -20}"
        echo ""
        export JWT_TOKEN="$TOKEN"
    else
        echo "❌ Failed to generate token"
        echo "Make sure python3-jose is installed"
        echo "Install with: pip3 install python-jose"
        exit 1
    fi
else
    echo "❌ python3 not found"
    exit 1
fi

# Step 5: Test Health Endpoint
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Test Health Endpoint"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/v1/health)
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HEALTH_CODE" = "200" ]; then
    echo "✅ Health check passed (200 OK)"
    echo ""
    echo "Response:"
    echo "$HEALTH_BODY" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_BODY"
else
    echo "❌ Health check failed (HTTP $HEALTH_CODE)"
fi

# Step 6: Test Chat Endpoint
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 6: Test Chat Endpoint with Authentication"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Skipping chat test - OPENAI_API_KEY not set"
else
    echo "Testing chat endpoint..."
    CHAT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/v1/chat/completions \
      -H "Authorization: Bearer $JWT_TOKEN" \
      -H "OPENAI_API_KEY: $OPENAI_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "messages": [{"role": "user", "content": "Say hello"}],
        "model": "openai/gpt-4.1"
      }')
    
    CHAT_CODE=$(echo "$CHAT_RESPONSE" | tail -n1)
    CHAT_BODY=$(echo "$CHAT_RESPONSE" | head -n-1)
    
    if [ "$CHAT_CODE" = "200" ]; then
        echo "✅ Chat endpoint working (200 OK)"
        echo ""
        echo "Response:"
        echo "$CHAT_BODY" | python3 -m json.tool 2>/dev/null || echo "$CHAT_BODY"
    else
        echo "❌ Chat endpoint failed (HTTP $CHAT_CODE)"
        echo ""
        echo "Response:"
        echo "$CHAT_BODY" | python3 -m json.tool 2>/dev/null || echo "$CHAT_BODY"
    fi
fi

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                          Setup Complete!                                  ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "📋 Summary:"
echo ""
echo "✅ Checks passed:"
echo "   • Server is running"
if redis-cli ping > /dev/null 2>&1; then
    echo "   • Redis is running"
fi
if [ ! -z "$OPENAI_API_KEY" ]; then
    echo "   • OpenAI API key is set"
fi
if [ ! -z "$JWT_TOKEN" ]; then
    echo "   • JWT token generated"
fi

echo ""
echo "🚀 Quick Commands:"
echo ""
echo "1. Run all examples:"
echo "   bash run_examples.sh"
echo ""
echo "2. Run Python client:"
echo "   python3 client.py"
echo ""
echo "3. Run a single curl command:"
echo ""
echo "   TOKEN=\$JWT_TOKEN"
echo "   curl -X POST http://localhost:8000/api/v1/chat/completions \\"
echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
echo "     -H \"OPENAI_API_KEY: \$OPENAI_API_KEY\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}],\"model\":\"openai/gpt-4.1\"}'"
echo ""
echo "📚 Documentation files:"
echo "   • API_KEY_QUICK_REFERENCE.md - Quick setup guide"
echo "   • API_KEY_REQUIREMENT.md - Complete guide with examples"
echo "   • CHAT_API_QUICKSTART.md - Quick start examples"
echo "   • CURL_EXAMPLES.md - Comprehensive curl reference"
echo ""
echo "✨ You're all set! Start testing now."
