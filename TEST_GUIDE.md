# Test Gateway - Testing Guide

## Overview

The `test_gateway.py` file provides comprehensive tests for all Enterprise AI Gateway endpoints without requiring authentication modifications.

## Running the Tests

```bash
# Make sure the server is running
uvicorn app.main:app --reload

# In another terminal, run the tests
python3 test_gateway.py
```

## Test Coverage

### 1. Health Check Endpoint (`/api/v1/health`)
- **Status**: ✅ Public (no auth required)
- **Tests**:
  - Validates 200 response
  - Checks response structure (status, redis_status, version, uptime_seconds)
  - Verifies Redis connectivity status

### 2. Authentication Error Scenarios
- **Missing Authorization Header**: Verify 401 error is returned
- **Invalid Authorization Format**: Verify proper format validation
- **Invalid JWT Token**: Verify token validation errors

### 3. Endpoint Accessibility
- **Tests all endpoints**: GET /health, GET /rate-limit, POST /chat/completions
- Verifies endpoints exist and don't return 404
- Checks appropriate status codes for auth-protected endpoints (401)

### 4. Documentation Endpoints
- **Swagger UI** (`/docs`): Interactive API documentation
- **OpenAPI JSON** (`/openapi.json`): Machine-readable API schema
- **ReDoc** (`/redoc`): Alternative API documentation viewer

### 5. Root Endpoint
- Tests the server's root path (`/`)

## Test Output Example

```
================================================================================
ENTERPRISE AI GATEWAY - TEST SUITE
================================================================================

Base URL: http://localhost:8000/api/v1

================================================================================
TEST: Health Check Endpoint
================================================================================
✅ Status Code: 200
✅ Response: {
  "status": "healthy",
  "redis_status": "connected",
  "version": "1.0.0",
  "uptime_seconds": 5.0,
  "details": null
}
✅ Status: healthy
✅ Redis: connected
✅ Version: 1.0.0
✅ Uptime: 5.0 seconds

...

================================================================================
TEST SUMMARY
================================================================================
✅ Passed: 9
❌ Failed: 0
📊 Total:  9

🎉 All tests passed!
================================================================================
```

## Test Structure

Each test suite is organized as a class with static methods:

```python
class TestHealthEndpoint:
    @staticmethod
    def test_health_check():
        # Test implementation
        pass
```

## Key Features

- ✅ **No external dependencies** beyond `requests`
- ✅ **Clear output** with emojis and formatted sections
- ✅ **Detailed assertions** with helpful error messages
- ✅ **Graceful error handling** for connection issues
- ✅ **Test summary** showing pass/fail counts
- ✅ **Extensible** - easy to add new tests

## Extending the Tests

To add a new test:

```python
class TestNewEndpoint:
    @staticmethod
    def test_new_feature():
        print("\n" + "="*80)
        print("TEST: New Feature")
        print("="*80)
        
        response = requests.get(f"{BASE_URL}/new-endpoint")
        assert response.status_code == 200
        
        print("✅ New feature test passed")
        return True
```

Then add it to the `test_suites` list in `run_all_tests()`.

## Endpoints Being Tested

| Endpoint | Method | Auth Required | Status |
|----------|--------|---------------|--------|
| `/api/v1/health` | GET | No | ✅ Public |
| `/api/v1/rate-limit` | GET | Yes | ✅ Protected |
| `/api/v1/chat/completions` | POST | Yes | ✅ Protected |
| `/docs` | GET | No | ✅ Public |
| `/openapi.json` | GET | No | ✅ Public |
| `/redoc` | GET | No | ✅ Public |

## Troubleshooting

### Connection Error
If you see: `Connection Error: Make sure the server is running`

Start the server:
```bash
cd enterprise-ai-gateway-mini
uvicorn app.main:app --reload
```

### Test Failures
- Check that Redis is running: `redis-cli ping`
- Verify the server is responding: `curl http://localhost:8000/api/v1/health`
- Check server logs for error messages

## Notes

- The test file is designed to work with the current gateway implementation
- No modifications to authentication are required
- Tests focus on endpoint accessibility and error handling
- All tests can be run independently or as a suite
