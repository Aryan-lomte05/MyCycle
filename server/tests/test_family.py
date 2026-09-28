import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.routes.family import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)

def test_family_invite_flow_and_privacy_guarantee():
    # 1. Create invite for partner
    resp = client.post("/v1/family/invite", json={"role": "partner", "expiry_hours": 24})
    assert resp.status_code == 200
    data = resp.json()
    code = data["invite_code"]
    assert code.startswith("MC-")

    # 2. Accept invite
    accept_resp = client.post("/v1/family/accept", json={"invite_code": code})
    assert accept_resp.status_code == 200
    token = accept_resp.json()["session_token"]

    # 3. View companion payload and assert NO raw cycle log fields exist
    view_resp = client.get("/v1/family/view", headers={"Authorization": f"Bearer {token}"})
    assert view_resp.status_code == 200
    view_data = view_resp.json()

    # STRICT PRIVACY ASSERTIONS
    forbidden_keys = ["cycle_length", "flow_intensity", "pain_score", "symptoms", "raw_logs", "start_date"]
    for key in forbidden_keys:
        assert key not in view_data, f"PRIVACY VIOLATION: '{key}' leaked into companion view!"

    assert view_data["role"] == "partner"
    assert "current_phase" in view_data
    assert "support_tip" in view_data

def test_revoke_flow():
    # Create & Accept
    resp = client.post("/v1/family/invite", json={"role": "parent", "expiry_hours": 12})
    code = resp.json()["invite_code"]
    token = client.post("/v1/family/accept", json={"invite_code": code}).json()["session_token"]

    # Revoke access
    revoke_resp = client.post("/v1/family/revoke", json={"invite_code": code})
    assert revoke_resp.status_code == 200

    # View attempt after revoke must be blocked (403)
    blocked_view = client.get("/v1/family/view", headers={"Authorization": f"Bearer {token}"})
    assert blocked_view.status_code == 403
