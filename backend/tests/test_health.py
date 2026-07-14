from unittest.mock import patch, MagicMock


def test_health(client):
    mock_conn = MagicMock()
    mock_connect = MagicMock()
    mock_connect.__enter__ = MagicMock(return_value=mock_conn)
    mock_connect.__exit__ = MagicMock(return_value=False)

    with patch("app.main.engine") as mock_engine:
        mock_engine.connect.return_value = mock_connect
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
