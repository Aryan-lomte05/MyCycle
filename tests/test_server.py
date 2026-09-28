"""Tests for FastAPI backend application (AD0 and AD5).

Verifies:
- /v1/health returns 200 and expected status.
- /v1/content/cards returns cards with topic filtering.
- /v1/content/messages returns message dictionary.
- /v1/reminders/rules returns rule definitions.
- /v1/metrics/aggregate accepts valid aggregate metrics.
- /v1/metrics/aggregate rejects payloads with raw cycle log fields or extra keys with 422.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "MyCycle"


def test_content_cards_endpoint():
    response = client.get("/v1/content/cards?lang=en")
    assert response.status_code == 200
    data = response.json()
    assert data["lang"] == "en"
    assert "cards" in data
    assert len(data["cards"]) > 0

    # Test topic filtering
    pcos_resp = client.get("/v1/content/cards?lang=en&topic=pcos")
    assert pcos_resp.status_code == 200
    pcos_data = pcos_resp.json()
    assert all(c["topic"] == "pcos" for c in pcos_data["cards"])


def test_content_messages_endpoint():
    response = client.get("/v1/content/messages?lang=en")
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    messages = data["messages"]
    assert "flag.pcos_pattern.v1" in messages
    assert "flag.anemia_pattern.v1" in messages
    assert "flag.thyroid_pattern.v1" in messages


def test_reminder_rules_endpoint():
    response = client.get("/v1/reminders/rules")
    assert response.status_code == 200
    data = response.json()
    assert data["evaluation"] == "on_device"
    assert "rules" in data
    assert len(data["rules"]) > 0


def test_aggregate_metrics_valid_submission():
    payload = {
        "metric_name": "app_opened_count",
        "value": 1.0
    }
    response = client.post("/v1/metrics/aggregate", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "recorded"
    assert data["metric_name"] == "app_opened_count"
    assert data["value"] == 1.0


def test_aggregate_metrics_rejects_raw_log_payload():
    # Attempting to submit cycle log data MUST fail with 422 Unprocessable Entity
    forbidden_payload = {
        "metric_name": "app_opened_count",
        "value": 1.0,
        "cycle_length_days": 32,
        "flow": 2,
        "pain": 5,
        "symptoms": {"acne": 2}
    }
    response = client.post("/v1/metrics/aggregate", json=forbidden_payload)
    assert response.status_code == 422


def test_aggregate_metrics_rejects_unapproved_metric_name():
    unapproved_payload = {
        "metric_name": "unauthorized_secret_metric",
        "value": 42.0
    }
    response = client.post("/v1/metrics/aggregate", json=unapproved_payload)
    assert response.status_code == 422


def test_docs_and_openapi_endpoints():
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    schema = openapi_resp.json()
    assert "paths" in schema
    assert "/v1/health" in schema["paths"]
    assert "/v1/content/cards" in schema["paths"]
    assert "/v1/reminders/rules" in schema["paths"]
    assert "/v1/metrics/aggregate" in schema["paths"]

