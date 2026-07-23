import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.shoebox.models import ShoeboxItem


def _make_item(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "workspace_id": uuid.uuid4(),
        "query": "SELECT * FROM post_rede_social_himark",
        "explanation": "test",
        "result": [{"time": "2020-04-06"}],
        "chart_spec": None,
        "ai_authored": False,
        "added_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    item = MagicMock(spec=ShoeboxItem)
    for k, v in defaults.items():
        setattr(item, k, v)
    return item


@patch("app.shoebox.router.list_items")
@patch("app.shoebox.router.get_db")
def test_list_shoebox(mock_db, mock_list, client):
    ws_id = uuid.uuid4()
    items = [_make_item(workspace_id=ws_id), _make_item(workspace_id=ws_id)]
    mock_list.return_value = items
    response = client.get(f"/api/workspaces/{ws_id}/shoebox")
    assert response.status_code == 200
    assert len(response.json()) == 2


@patch("app.shoebox.router.force_extract")
@patch("app.shoebox.router.add_item")
@patch("app.shoebox.router.get_db")
def test_add_to_shoebox(mock_db, mock_add, mock_extract, client):
    ws_id = uuid.uuid4()
    item = _make_item(workspace_id=ws_id)
    mock_add.return_value = item
    response = client.post(
        f"/api/workspaces/{ws_id}/shoebox",
        json={
            "query": "SELECT * FROM post_rede_social_himark",
            "explanation": "test",
            "result": [{"time": "2020-04-06"}],
        },
    )
    assert response.status_code == 201
    assert response.json()["query"] == "SELECT * FROM post_rede_social_himark"


@patch("app.shoebox.router.get_item")
@patch("app.shoebox.router.get_db")
def test_get_shoebox_item(mock_db, mock_get, client):
    ws_id = uuid.uuid4()
    item_id = uuid.uuid4()
    item = _make_item(id=item_id, workspace_id=ws_id)
    mock_get.return_value = item
    response = client.get(f"/api/workspaces/{ws_id}/shoebox/{item_id}")
    assert response.status_code == 200
    assert response.json()["query"] == "SELECT * FROM post_rede_social_himark"


@patch("app.shoebox.router.get_item")
@patch("app.shoebox.router.get_db")
def test_get_shoebox_item_not_found(mock_db, mock_get, client):
    ws_id = uuid.uuid4()
    mock_get.return_value = None
    response = client.get(f"/api/workspaces/{ws_id}/shoebox/{uuid.uuid4()}")
    assert response.status_code == 404


@patch("app.shoebox.router.remove_item")
@patch("app.shoebox.router.get_db")
def test_remove_from_shoebox(mock_db, mock_remove, client):
    ws_id = uuid.uuid4()
    mock_remove.return_value = True
    response = client.delete(f"/api/workspaces/{ws_id}/shoebox/{uuid.uuid4()}")
    assert response.status_code == 204


@patch("app.shoebox.router.remove_item")
@patch("app.shoebox.router.get_db")
def test_remove_not_in_shoebox(mock_db, mock_remove, client):
    ws_id = uuid.uuid4()
    mock_remove.return_value = False
    response = client.delete(f"/api/workspaces/{ws_id}/shoebox/{uuid.uuid4()}")
    assert response.status_code == 404
