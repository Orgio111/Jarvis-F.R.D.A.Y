from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Force safe defaults before importing app
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("GPU_REQUIRED", "false")
os.environ.setdefault("NVIDIA_NIM_API_KEY", "")
os.environ.setdefault("OPENROUTER_API_KEY", "")
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c
