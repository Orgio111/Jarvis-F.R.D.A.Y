from __future__ import annotations


def test_vision_status(client):
    r = client.get("/vision/status")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert "enabled" in data
    assert "maxImageSizeMb" in data


def test_vision_analyze_requires_image(client):
    # Missing required file field → 422 or 503 if vision disabled
    r = client.post("/vision/analyze")
    assert r.status_code in (422, 503)
