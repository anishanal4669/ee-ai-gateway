# Enterprise AI Gateway Mini Project

A production-ready FastAPI-based AI Gateway that accepts prompts with JWT tokens, validates them, routes requests to appropriate models, and implements comprehensive logging with rate limiting.

## 🎯 Features

- **JWT Token Validation**: Decode and validate JWT tokens with signature verification
- **Multi-Model Routing**: Route requests to appropriate foundation models based on token claims
- **Rate Limiting**: Implement sliding window and token-bucket rate limiting per user
- **Comprehensive Logging**: Structured logging with request tracking, performance metrics, and audit trails
- **Request/Response Handling**: Standardized request/response formats with error handling
- **Monitoring & Metrics**: Built-in metrics collection for Prometheus integration
- **Security**: PII masking, encryption, and secure token handling

## 📁 Project Structure

```
enterprise-ai-gateway-mini/
├── README.md
├── requirements.txt
├── .env.example
├── config/
│   ├── __init__.py
│   └── settings.py              # Configuration management
├── models/
│   ├── __init__.py
│   ├── schemas.py               # Request/response schemas
│   └── models.py                # Model registry
├── auth/
│   ├── __init__.py
│   ├── jwt_handler.py           # JWT validation & decoding
│   └── permissions.py           # RBAC and permissions
├── gateway/
│   ├── __init__.py
│   ├── router.py                # Main gateway router
│   ├── rate_limiter.py          # Rate limiting implementation
│   └── model_router.py          # Model routing logic
├── logging_config/
│   ├── __init__.py
│   ├── logger.py                # Logging setup
│   └── middleware.py            # Request/response middleware
├── utils/
│   ├── __init__.py
│   ├── metrics.py               # Prometheus metrics
│   └── pii_masker.py            # PII masking utilities
├── main.py                      # FastAPI application entry point
├── docker-compose.yml           # Local development setup
└── tests/
    ├── __init__.py
    ├── test_jwt_validation.py
    ├── test_rate_limiting.py
    ├── test_model_routing.py
    └── test_end_to_end.py
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose (optional)

### Installation

1. **Clone/Navigate to project**:
```bash
cd enterprise-ai-gateway-mini
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Setup environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run the application**:
```bash
# run from the project root
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The gateway will be available at `http://localhost:8000` (default). The repo includes example scripts (`run_examples.sh`) and a simple `client.py` to exercise the endpoints during development.

## 📚 API Documentation

### Generate JWT Token (for testing)

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "username": "advisor@wealth.com",
    "lob": "wealth",
    "models": ["gpt-4", "llama"],
    "rate_limit": 100
  }'
```

### Chat Completions (OpenAI-compatible)

The gateway exposes an OpenAI-compatible chat completions endpoint at `/api/v1/chat/completions`. It accepts the usual model + messages payload and will route to the configured upstream provider on your behalf.

Example (gateway uses its configured upstream API key from `.env`):

```bash
curl -v -X POST "http://localhost:8000/api/v1/chat/completions" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-4.1",
    "messages": [{"role": "user", "content": "Write a short haiku about programming"}]
  }'
```

Override the gateway upstream key per-request (testing only) with a supported header such as `openai-api-key` or `X-API-Key`:

```bash
curl -v -X POST "http://localhost:8000/api/v1/chat/completions" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "openai-api-key: <UPSTREAM_OPENAI_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-4.1","messages":[{"role":"user","content":"Say hello."}]}'
```

### Response Format

**Success (200 OK)**:
```json
{
  "request_id": "req_1234567890",
  "status": "success",
  "model": "gpt-4",
  "response": "The portfolio is well-diversified...",
  "metadata": {
    "tokens_used": 125,
    "latency_ms": 1234,
    "timestamp": "2026-02-01T10:30:00Z"
  }
}
```

**Error (4xx/5xx)**:
```json
{
  "request_id": "req_1234567890",
  "status": "error",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "User has exceeded rate limit (100 requests/hour)",
  "details": {
    "current_count": 100,
    "limit": 100,
    "reset_at": "2026-02-01T11:30:00Z"
  }
}
```

## 🔐 Security Features

### JWT Token Structure
```json
{
  "sub": "advisor@wealth.com",
  "lob": "wealth",
  "models": ["gpt-4", "llama"],
  "permissions": ["read:portfolio", "write:recommendations"],
  "rate_limit": 100,
  "exp": 1704067200,
  "iat": 1704063600
}
```

### Rate Limiting
- **Sliding Window Algorithm**: Precise rate limiting per user
- **Token Bucket Algorithm**: Burst traffic handling
- **Configurable Limits**: Per-user, per-model, per-LoB limits
- **Graceful Degradation**: Clear error messages with reset times

### Logging
- **Structured Logging**: JSON format for easy parsing
- **Request Tracking**: Unique request IDs for tracing
- **Performance Metrics**: Latency, token usage, model selection
- **Audit Trail**: All API calls logged with user, timestamp, action
- **PII Masking**: Automatic masking of sensitive information

## 📊 Monitoring

### Prometheus Metrics
```
# Request counters
ai_gateway_requests_total{model="gpt-4",status="success"}
ai_gateway_requests_total{model="gpt-4",status="error"}

# Latency histograms
ai_gateway_request_duration_seconds{model="gpt-4"}

# Rate limit metrics
ai_gateway_rate_limit_hits{user_id="advisor123"}

# Token usage
ai_gateway_tokens_used{model="gpt-4"}
```

Access metrics at: `http://localhost:8000/metrics`

## 🧪 Testing

### Run All Tests
```bash
pytest
```

### Run Specific Tests
```bash
pytest tests/test_jwt_validation.py -v
pytest tests/test_rate_limiting.py -v
pytest tests/test_model_routing.py -v
pytest tests/test_end_to_end.py -v
```

### Generate Coverage Report
```bash
pytest --cov=. --cov-report=html
```

## 📝 Configuration

### Environment Variables (.env)

```
# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Rate Limiting
RATE_LIMIT_ALGORITHM=sliding_window  # or token_bucket
RATE_LIMIT_DEFAULT_PER_HOUR=100
RATE_LIMIT_BURST_SIZE=10

# Model Configuration
DEFAULT_MODEL=gpt-4
AVAILABLE_MODELS=gpt-4,llama-2,mistral
MODEL_API_TIMEOUT=30

# Upstream provider API keys (do NOT check secrets into source control)
OPENAI_API_KEY=sk-...                     # used by models.yaml placeholder ${OPENAI_API_KEY}
ANTHROPIC_API_KEY=claude-...
LLAMA2_API_KEY=llama-...

### Logging
- **Structured Logging**: JSON format for easy parsing
- **Request Tracking**: Unique request IDs for tracing
- **Performance Metrics**: Latency, token usage, model selection
- **Audit Trail**: All API calls logged with user, timestamp, action
- **PII Masking**: Automatic masking of sensitive information
- **Secrets handling**: The gateway is deliberately defensive: raw Authorization headers (JWTs) and full upstream API keys are never written to logs. Logs include masked previews and short hash prefixes for correlation only. If you have historical logs that contain secrets, rotate and redact them immediately.

# PII Masking
ENABLE_PII_MASKING=true
PATTERNS_TO_MASK=email,phone,ssn,account_number

# Monitoring
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
```

## 🔄 Request Flow

```
1. Client sends request with JWT token
   ↓
2. JWT Middleware validates token signature
   ↓
3. Extract claims: user_id, lob, permissions, rate_limit
   ↓
4. Check rate limit (current usage vs quota)
   ↓
5. Validate prompt & model selection
   ↓
6. Route to appropriate model based on claims
   ↓
7. Call model API (with retry logic)
   ↓
8. Log request details (structured logging)
   ↓
9. Record metrics (latency, tokens, success/failure)
   ↓
10. Return response to client
```

## 🏗️ Architecture Decisions

### JWT Validation
- **Library**: PyJWT for validation
- **Storage**: In-memory cache of public keys (refreshed every hour)
- **Revocation**: Token blacklist for immediate revocation

### Rate Limiting
- **Default Algorithm**: Sliding Window (more accurate than token bucket)
- **Storage**: Redis for distributed rate limiting
- **Fallback**: In-memory storage for single-instance deployments

### Model Routing
- **Strategy**: Based on user's allowed models + performance metrics
- **Load Balancing**: Round-robin across multiple endpoints
- **Fallback**: Auto-retry with alternative model if first fails

### Logging
- **Format**: Structured JSON for machine parsing
- **Correlation**: Request IDs for tracing across services
- **Retention**: 30 days (configurable)

## 🚢 Deployment

### Docker Deployment
```bash
docker-compose up -d
```

### Kubernetes Deployment
See `k8s-deployment.yaml` for Kubernetes manifests

### Cloud Deployment
- **Azure Container Instances**: See azure/aci-deploy.sh
- **AWS Lambda**: See aws/lambda-deploy.py
- **GCP Cloud Run**: See gcp/cloud-run-deploy.sh

## 📚 Design Patterns Used

1. **Factory Pattern**: Model instantiation based on type
2. **Strategy Pattern**: Rate limiting algorithms (sliding window, token bucket)
3. **Observer Pattern**: Logging middleware
4. **Decorator Pattern**: JWT validation decorators
5. **Circuit Breaker Pattern**: Model API failure handling

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Add tests for new functionality
3. Run linting: `pylint src/`
4. Submit pull request

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Troubleshooting

### JWT Token Expired
```
Error: "Token has expired"
Solution: Generate new token using /auth/token endpoint
```

### Rate Limit Exceeded
```
Error: "Rate limit exceeded"
Solution: Wait for reset time or contact admin for increased quota
```

### Model Not Available
```
Error: "Model 'gpt-5' not available for your LoB"
Solution: Use one of: gpt-4, llama-2, mistral (check JWT claims)
```

## 📞 Support

For issues, questions, or feature requests:
1. Check existing issues in GitHub
2. Create detailed bug report with logs
3. Contact: https://medium.com/@anishanal4669

---

**Last Updated**: February 1, 2026
**Version**: 1.0.0
