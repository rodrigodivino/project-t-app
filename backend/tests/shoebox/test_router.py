import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.shoebox.models import ShoeboxItem


def _make_item(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "workspace_id": uuid.uuid4(),
        "source_document_id": uuid.uuid4(),
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


@patch("app.shoebox.router.add_item")
@patch("app.shoebox.router.get_db")
def test_add_to_shoebox(mock_db, mock_add, client):
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    item = _make_item(workspace_id=ws_id, source_document_id=doc_id)
    mock_add.return_value = item
    response = client.post(
        f"/api/workspaces/{ws_id}/shoebox",
        json={"source_document_id": str(doc_id)},
    )
    assert response.status_code == 201
    assert response.json()["source_document_id"] == str(doc_id)


@patch("app.shoebox.router.remove_item")
@patch("app.shoebox.router.get_db")
def test_remove_from_shoebox(mock_db, mock_remove, client):
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    mock_remove.return_value = True
    response = client.delete(f"/api/workspaces/{ws_id}/shoebox/{doc_id}")
    assert response.status_code == 204


@patch("app.shoebox.router.remove_item")
@patch("app.shoebox.router.get_db")
def test_remove_not_in_shoebox(mock_db, mock_remove, client):
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    mock_remove.return_value = False
    response = client.delete(f"/api/workspaces/{ws_id}/shoebox/{doc_id}")
    assert response.status_code == 404
