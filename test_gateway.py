"""
Simple test suite for Enterprise AI Gateway endpoints

Tests:
- Health check endpoint (/api/v1/health)
- Rate limit status endpoint (/api/v1/rate-limit)
- Chat completions endpoint (/api/v1/chat/completions)
"""

import requests
import json
from datetime import datetime, timedelta, timezone

# Configuration
BASE_URL = "http://localhost:8000/api/v1"


class TestHealthEndpoint:
    """Test /health endpoint - No authentication required"""
    
    @staticmethod
    def test_health_check():
        """Test successful health check"""
        print("\n" + "="*80)
        print("TEST: Health Check Endpoint")
        print("="*80)
        
        response = requests.get(f"{BASE_URL}/health")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response: {json.dumps(data, indent=2)}")
        
        # Validate response structure
        assert "status" in data, "Missing 'status' field"
        assert "redis_status" in data, "Missing 'redis_status' field"
        assert "version" in data, "Missing 'version' field"
        assert "uptime_seconds" in data, "Missing 'uptime_seconds' field"
        
        print(f"✅ Status: {data['status']}")
        print(f"✅ Redis: {data['redis_status']}")
        print(f"✅ Version: {data['version']}")
        print(f"✅ Uptime: {data['uptime_seconds']} seconds")
        
        return True


class TestAuthenticationErrors:
    """Test authentication error scenarios"""
    
    @staticmethod
    def test_missing_auth_header():
        """Test request without authorization header"""
        print("\n" + "="*80)
        print("TEST: Missing Authorization Header")
        print("="*80)
        
        response = requests.get(f"{BASE_URL}/rate-limit")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Error: {data.get('detail', 'No detail provided')}")
        
        return True
    
    @staticmethod
    def test_invalid_auth_format():
        """Test request with invalid authorization format"""
        print("\n" + "="*80)
        print("TEST: Invalid Authorization Format")
        print("="*80)
        
        headers = {"Authorization": "InvalidFormat"}
        response = requests.get(f"{BASE_URL}/rate-limit", headers=headers)
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Error: {data.get('detail', 'No detail provided')}")
        
        return True
    
    @staticmethod
    def test_invalid_token():
        """Test request with invalid JWT token"""
        print("\n" + "="*80)
        print("TEST: Invalid JWT Token")
        print("="*80)
        
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = requests.get(f"{BASE_URL}/rate-limit", headers=headers)
        
        # Can be 401 (auth error) or 500 (validation error) depending on implementation
        assert response.status_code in [401, 500], f"Expected 401 or 500, got {response.status_code}"
        data = response.json()
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Error: {data.get('detail', 'No detail provided')}")
        
        return True


class TestEndpointAccessibility:
    """Test that endpoints are accessible and respond correctly"""
    
    @staticmethod
    def test_endpoints_exist():
        """Test that all endpoints exist and are accessible"""
        print("\n" + "="*80)
        print("TEST: Endpoint Accessibility")
        print("="*80)
        
        endpoints = [
            ("GET", "/health"),
            ("GET", "/rate-limit"),
            ("POST", "/chat/completions"),
        ]
        
        for method, endpoint in endpoints:
            url = f"{BASE_URL}{endpoint}"
            
            if method == "GET":
                response = requests.get(url)
            else:
                # POST requires a body
                response = requests.post(url, json={})
            
            # We expect either success or auth error (not 404)
            assert response.status_code != 404, f"{endpoint} not found (404)"
            
            print(f"✅ {method} {endpoint} - Status: {response.status_code}")
        
        return True


class TestSwaggerDocs:
    """Test Swagger/OpenAPI documentation endpoints"""
    
    @staticmethod
    def test_swagger_ui():
        """Test Swagger UI endpoint"""
        print("\n" + "="*80)
        print("TEST: Swagger UI Endpoint")
        print("="*80)
        
        response = requests.get("http://localhost:8000/docs")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ Swagger UI available at http://localhost:8000/docs")
        
        return True
    
    @staticmethod
    def test_openapi_json():
        """Test OpenAPI JSON schema endpoint"""
        print("\n" + "="*80)
        print("TEST: OpenAPI JSON Endpoint")
        print("="*80)
        
        response = requests.get("http://localhost:8000/openapi.json")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "openapi" in data or "swagger" in data, "Invalid OpenAPI schema"
        print(f"✅ OpenAPI schema available at http://localhost:8000/openapi.json")
        
        return True
    
    @staticmethod
    def test_redoc():
        """Test ReDoc endpoint"""
        print("\n" + "="*80)
        print("TEST: ReDoc Endpoint")
        print("="*80)
        
        response = requests.get("http://localhost:8000/redoc")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ ReDoc available at http://localhost:8000/redoc")
        
        return True


class TestRootEndpoint:
    """Test root endpoint"""
    
    @staticmethod
    def test_root_redirect():
        """Test root endpoint"""
        print("\n" + "="*80)
        print("TEST: Root Endpoint")
        print("="*80)
        
        response = requests.get("http://localhost:8000/", allow_redirects=False)
        
        # Could be 200 (success), 301/302 (redirect), or 404 (not found)
        assert response.status_code in [200, 301, 302, 404], \
            f"Unexpected status: {response.status_code}"
        
        print(f"✅ Root endpoint status: {response.status_code}")
        
        return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("ENTERPRISE AI GATEWAY - TEST SUITE")
    print("="*80)
    print("\nBase URL: " + BASE_URL)
    
    test_suites = [
        ("Health Check", TestHealthEndpoint.test_health_check),
        ("Missing Auth Header", TestAuthenticationErrors.test_missing_auth_header),
        ("Invalid Auth Format", TestAuthenticationErrors.test_invalid_auth_format),
        ("Invalid Token", TestAuthenticationErrors.test_invalid_token),
        ("Endpoint Accessibility", TestEndpointAccessibility.test_endpoints_exist),
        ("Swagger UI", TestSwaggerDocs.test_swagger_ui),
        ("OpenAPI JSON", TestSwaggerDocs.test_openapi_json),
        ("ReDoc", TestSwaggerDocs.test_redoc),
        ("Root Endpoint", TestRootEndpoint.test_root_redirect),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in test_suites:
        try:
            test_func()
            passed += 1
        except requests.exceptions.ConnectionError as e:
            print(f"\n❌ Connection Error: {e}")
            print(f"   Make sure the server is running: uvicorn app.main:app --reload")
            failed += 1
        except AssertionError as e:
            print(f"\n❌ Assertion Failed: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ Error: {e}")
            failed += 1
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total:  {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed")
    
    print("="*80 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
