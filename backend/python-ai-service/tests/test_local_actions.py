from __future__ import annotations


def test_local_actions_list(client):
    r = client.get("/local-actions")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True


def test_local_actions_pending_empty(client):
    r = client.get("/local-actions/pending")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "pending" in body["data"]


def test_execute_unknown_action(client):
    r = client.post("/local-actions/nonexistent_action/execute", json={})
    # Either 404 (not found) or 503 (disabled) — both are valid envelopes
    assert r.status_code in (404, 503)
    body = r.json()
    assert body["ok"] is False


def test_approve_unknown_approval(client):
    r = client.post("/local-actions/approvals/apr_missing/approve")
    assert r.status_code == 404
    body = r.json()
    assert body["ok"] is False


def test_deny_unknown_approval(client):
    r = client.post("/local-actions/approvals/apr_missing/deny")
    assert r.status_code == 404
    body = r.json()
    assert body["ok"] is False
