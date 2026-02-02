#!/bin/bash
# Copy-paste ready examples for testing the chat/completions endpoint

# ==============================================================================
# SETUP - Run these first
# ==============================================================================

# 1. Start the server (in a separate terminal)
# cd enterprise-ai-gateway-mini
# uvicorn app.main:app --reload

# 2. Generate a token (copy the token from output)
# python3 generate_token.py

# ==============================================================================
# HEALTH CHECK - No authentication required
# ==============================================================================

echo "Testing Health Endpoint..."
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool


# ==============================================================================
# CHAT COMPLETIONS - Copy and paste examples
# ==============================================================================

TOKEN=$(python3 utils/get_token.py)

# ============ EXAMPLE 1: Simple Question ============
echo ""
echo "===== EXAMPLE 1: Simple Question ====="
curl -s -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is artificial intelligence?"}
    ],
    "model": "openai/gpt-4.1",
    "temperature": 0.7,
    "max_tokens": 500
  }' | python3 -m json.tool


# ============ EXAMPLE 2: Creative Prompt ============
echo ""
echo "===== EXAMPLE 2: Creative Prompt (High Temperature) ====="
curl -s -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Write a short poem about programming"}
    ],
    "model": "openai/gpt-4.1",
    "temperature": 0.9,
    "max_tokens": 300
  }' | python3 -m json.tool


# ============ EXAMPLE 3: Professional Tone ============
echo ""
echo "===== EXAMPLE 3: Professional Tone (Low Temperature) ====="
curl -s -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain machine learning algorithms"}
    ],
    "model": "openai/gpt-4.1",
    "temperature": 0.3,
    "max_tokens": 500
  }' | python3 -m json.tool


# ============ EXAMPLE 4: Multi-Turn Conversation ============
echo ""
echo "===== EXAMPLE 4: Multi-Turn Conversation ====="
curl -v -X POST "http://localhost:8000/api/v1/chat/completions" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{ "model": "openai/gpt-4.1", "messages": [ {"role":"user","content":"What is the Capital of India"} ] }'


# ============ EXAMPLE 5: Using Different Model ============
echo ""
echo "===== EXAMPLE 5: Using gpt-3.5-turbo ====="
curl -s -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain quantum computing"}
    ],
    "model": "llama-2-7b-mini",
    "temperature": 0.7,
    "max_tokens": 500
  }' | python3 -m json.tool


# ============ EXAMPLE 6: Extract Only Response ============
echo ""
echo "===== EXAMPLE 6: Extract Only the Response Text ====="
curl -s -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "openai-api-key: $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Say hello in 5 different languages"}
    ],
    "model": "openai/gpt-4.1"
  }' | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('response', 'No response'))"


# ============ EXAMPLE 7: Anthropic (x-api-key header) ============
echo ""
echo "===== EXAMPLE 7: Anthropic (claude-sonnet-4) ====="
curl -s -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Summarize the following text: AI governance best practices"}
    ],
    "model": "anthropic/claude-sonnet-4",
    "max_tokens": 300
  }' | python3 -m json.tool


# ============ EXAMPLE 7: Check Rate Limit ============
echo ""
echo "===== EXAMPLE 7: Check Rate Limit Status ====="
curl -s -X GET http://localhost:8000/api/v1/rate-limit \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool


# ============ EXAMPLE 8: Error - Missing Token ============
echo ""
echo "===== EXAMPLE 8: Error - Missing Authorization Header ====="
curl -s -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello"}
    ],
    "model": "gpt-4"
  }' | python3 -m json.tool


# ==============================================================================
# SAVE TO FILE
# ==============================================================================

echo ""
echo "✅ All examples completed!"
echo ""
echo "To save responses to file:"
echo "  curl ... > response.json"
echo ""
echo "To view in nice format:"
echo "  cat response.json | python3 -m json.tool"
