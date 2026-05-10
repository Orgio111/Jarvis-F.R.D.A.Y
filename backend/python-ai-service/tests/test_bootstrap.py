from __future__ import annotations


def test_bootstrap_returns_envelope(client):
    r = client.get("/bootstrap")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert "features" in data
    assert "settings" in data


def test_bootstrap_features_are_bools(client):
    r = client.get("/bootstrap")
    features = r.json()["data"]["features"]
    for key, val in features.items():
        assert isinstance(val, bool), f"feature {key!r} is not bool: {val!r}"


def test_bootstrap_settings_no_secrets(client):
    r = client.get("/bootstrap")
    settings = r.json()["data"]["settings"]
    # Ensure no raw API keys leak into bootstrap payload
    for key in settings:
        assert "key" not in key.lower() or settings[key] in (True, False, None, ""), \
            f"Potential secret leakage in settings.{key}"
