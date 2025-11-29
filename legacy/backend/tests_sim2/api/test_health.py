from __future__ import annotations

from fastapi.testclient import TestClient

import loopforge.api.app as api_app


def test_health_endpoint():
    client = TestClient(api_app.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
