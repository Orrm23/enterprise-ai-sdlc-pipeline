"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"


def test_create_order_api_success():
    payload = {
        "customer_id": "cust_abc123",
        "items": [
            {"sku": "SKU-KEYBOARD", "quantity": 1, "unit_price": 75.0}
        ],
        "discount_code": "WELCOME10"
    }
    response = client.post("/api/v1/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_id"] == "cust_abc123"
    assert data["subtotal"] == 75.0
    assert data["discount_amount"] == 7.5
    assert "order_id" in data


def test_create_order_invalid_discount():
    payload = {
        "customer_id": "cust_xyz789",
        "items": [
            {"sku": "SKU-MONITOR", "quantity": 1, "unit_price": 300.0}
        ],
        "discount_code": "NON_EXISTENT_PROMO"
    }
    response = client.post("/api/v1/orders", json=payload)
    assert response.status_code == 400
    assert "invalid or expired" in response.json()["detail"]


def test_get_order_not_found():
    response = client.get("/api/v1/orders/non_existent_id")
    assert response.status_code == 404
