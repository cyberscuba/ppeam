import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_request_otp():
    """Test OTP request endpoint"""
    response = client.post("/auth/otp/request", json={
        "phone": "+573001234567",
        "full_name": "Test User"
    })
    assert response.status_code in [200, 429]  # 429 if rate limited

def test_invalid_phone():
    """Test invalid phone number"""
    response = client.post("/auth/otp/request", json={
        "phone": "invalid",
        "full_name": "Test User"
    })
    assert response.status_code == 400

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
