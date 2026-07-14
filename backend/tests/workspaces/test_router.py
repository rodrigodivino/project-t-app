import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.workspaces.models import Workspace


def _make_ws(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test",
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    ws = MagicMock(spec=Workspace)
    for k, v in defaults.items():
        setattr(ws, k, v)
    return ws


@patch("app.workspaces.router.list_workspaces")
@patch("app.workspaces.router.get_db")
def test_list_workspaces(mock_db, mock_list, client):
    items = [_make_ws(name="A"), _make_ws(name="B")]
    mock_list.return_value = items
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    assert len(response.json()) == 2


@patch("app.workspaces.router.create_workspace")
@patch("app.workspaces.router.get_db")
def test_create_workspace(mock_db, mock_create, client):
    ws = _make_ws(name="New")
    mock_create.return_value = ws
    response = client.post("/api/workspaces", json={"name": "New"})
    assert response.status_code == 201
    assert response.json()["name"] == "New"


@patch("app.workspaces.router.get_workspace")
@patch("app.workspaces.router.get_db")
def test_get_workspace_found(mock_db, mock_get, client):
    ws = _make_ws()
    mock_get.return_value = ws
    response = client.get(f"/api/workspaces/{ws.id}")
    assert response.status_code == 200


@patch("app.workspaces.router.get_workspace")
@patch("app.workspaces.router.get_db")
def test_get_workspace_not_found(mock_db, mock_get, client):
    mock_get.return_value = None
    response = client.get(f"/api/workspaces/{uuid.uuid4()}")
    assert response.status_code == 404


@patch("app.workspaces.router.delete_workspace")
@patch("app.workspaces.router.get_db")
def test_delete_workspace(mock_db, mock_delete, client):
    mock_delete.return_value = True
    response = client.delete(f"/api/workspaces/{uuid.uuid4()}")
    assert response.status_code == 204


@patch("app.workspaces.router.delete_workspace")
@patch("app.workspaces.router.get_db")
def test_delete_workspace_not_found(mock_db, mock_delete, client):
    mock_delete.return_value = False
    response = client.delete(f"/api/workspaces/{uuid.uuid4()}")
    assert response.status_code == 404
