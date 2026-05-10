from __future__ import annotations


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "status" in body["data"]


def test_health_has_version(client):
    r = client.get("/health")
    data = r.json()["data"]
    assert "version" in data


def test_health_cors_header(client):
    r = client.get("/health", headers={"Origin": "http://localhost:8000"})
    assert r.status_code == 200
