import pytest
from fastapi.testclient import TestClient

from app.auth.dependency import require_auth
from app.main import app


@pytest.fixture
def client():
    app.dependency_overrides[require_auth] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()
