from __future__ import annotations


def test_search_status(client):
    r = client.get("/search/status")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert "enabled" in data
    assert "engine" in data


def test_search_requires_query(client):
    r = client.post("/search", json={})
    assert r.status_code == 400
    body = r.json()
    assert body["ok"] is False


def test_search_with_query(client):
    # Search may fail if web is disabled, but must return a valid envelope
    r = client.post("/search", json={"query": "python programming", "maxResults": 3})
    assert r.status_code in (200, 503)
    body = r.json()
    assert "ok" in body


def test_search_invalid_body(client):
    r = client.post("/search", content=b"not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400
