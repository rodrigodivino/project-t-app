from unittest.mock import patch


@patch("app.sources.router.execute_query")
@patch("app.sources.router.get_db")
def test_query_success(mock_db, mock_exec, client):
    mock_exec.return_value = [
        {"time": "2020-04-06", "location": "Broadview", "account": "user1", "message": "hello"}
    ]
    response = client.post(
        "/api/workspaces/00000000-0000-0000-0000-000000000001/sources/query",
        json={"query": "SELECT * FROM post_rede_social_himark LIMIT 1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["location"] == "Broadview"


@patch("app.sources.router.execute_query")
@patch("app.sources.router.get_db")
def test_query_rejects_non_select(mock_db, mock_exec, client):
    mock_exec.side_effect = ValueError("Only SELECT queries are allowed")
    response = client.post(
        "/api/workspaces/00000000-0000-0000-0000-000000000001/sources/query",
        json={"query": "DELETE FROM post_rede_social_himark"},
    )
    assert response.status_code == 400
    assert "Only SELECT" in response.json()["detail"]
