from __future__ import annotations


def test_si_status(client):
    r = client.get("/self-improvement/status")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert "enabled" in data
    assert "pendingSuggestions" in data


def test_si_list_suggestions_empty(client):
    r = client.get("/self-improvement/suggestions")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "suggestions" in body["data"]


def test_si_suggest_requires_context(client):
    r = client.post("/self-improvement/suggest", json={})
    # Either 400 (bad request) or 503 (disabled) — both are valid
    assert r.status_code in (400, 503)
    body = r.json()
    assert body["ok"] is False


def test_si_approve_unknown(client):
    r = client.post("/self-improvement/suggestions/sug_missing/approve")
    assert r.status_code == 404


def test_si_reject_unknown(client):
    r = client.post("/self-improvement/suggestions/sug_missing/reject")
    assert r.status_code == 404
