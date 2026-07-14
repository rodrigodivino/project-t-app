from unittest.mock import patch


def test_verify_valid_code(client):
    with patch("app.auth.service.ACCESS_CODE", "test"):
        response = client.post("/api/auth/verify", json={"code": "test"})
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_verify_invalid_code(client):
    with patch("app.auth.service.ACCESS_CODE", "test"):
        response = client.post("/api/auth/verify", json={"code": "wrong"})
    assert response.status_code == 200
    assert response.json()["valid"] is False
