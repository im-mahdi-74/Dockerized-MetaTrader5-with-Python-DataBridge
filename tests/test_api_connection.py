# tests/test_api_connection.py

import os
import requests

API_URL = os.environ.get("API_URL", "http://localhost:8080")
API_KEY = os.environ.get("API_KEY", "")

def test_health_endpoint():
    """
    Test the health endpoint to ensure the API is reachable.
    """
    response = requests.get(f"{API_URL}/health", timeout=10)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    response_data = response.json()
    assert response_data.get("status") == "ok", "API is not healthy"

def test_api_connection():
    """
    Test a valid API request with correct authentication.
    """
    if not API_KEY:
        import pytest
        pytest.skip("API_KEY environment variable is not set.")

    request_payload = {
        "function_name": "account_info"
    }

    request_headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }

    response = requests.post(f"{API_URL}/rpc", headers=request_headers, json=request_payload, timeout=10)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    
    response_data = response.json()
    assert response_data.get("status") == "success", "Response status is not 'success'"
    assert response_data.get("function_name") == "account_info", "Function name in response is incorrect"
    assert "data" in response_data, "Response is missing 'data' field"
    assert "login" in response_data["data"], "Account data is missing 'login' field"
    assert "balance" in response_data["data"], "Account data is missing 'balance' field"

def test_unauthorized_access():
    """
    Test an API request without providing an API key, expecting a 401 Unauthorized response.
    """
    request_payload = {
        "function_name": "account_info"
    }

    request_headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(f"{API_URL}/rpc", headers=request_headers, json=request_payload, timeout=10)
    assert response.status_code == 401, f"Expected status code 401, got {response.status_code}"

def test_disallowed_function():
    """
    Test calling a disallowed function (e.g., 'initialize'), expecting a 403 Forbidden response.
    """
    if not API_KEY:
        import pytest
        pytest.skip("API_KEY environment variable is not set.")

    request_payload = {
        "function_name": "initialize"
    }

    request_headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }

    response = requests.post(f"{API_URL}/rpc", headers=request_headers, json=request_payload, timeout=10)
    assert response.status_code == 403, f"Expected status code 403, got {response.status_code}"