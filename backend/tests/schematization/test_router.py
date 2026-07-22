import uuid
from unittest.mock import MagicMock, patch

from app.schematization.models import Schematization


def _make_schema(ws_id=None, data=None):
    ws_id = ws_id or uuid.uuid4()
    data = data if data is not None else []
    row = MagicMock(spec=Schematization)
    row.workspace_id = ws_id
    row.data = data
    return row


@patch("app.schematization.router.get_or_create")
@patch("app.schematization.router.get_db")
def test_get_schematization(mock_db, mock_get, client):
    ws_id = uuid.uuid4()
    mock_get.return_value = _make_schema(ws_id)
    response = client.get(f"/api/workspaces/{ws_id}/schematization")
    assert response.status_code == 200
    assert response.json()["data"] == []


@patch("app.schematization.router.add_evidence")
@patch("app.schematization.router.get_db")
def test_add_evidence(mock_db, mock_add, client):
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    mock_add.return_value = _make_schema(
        ws_id, [{"type": "evidence", "id": str(ev_id)}]
    )
    response = client.post(
        f"/api/workspaces/{ws_id}/schematization/evidence",
        json={"evidence_id": str(ev_id)},
    )
    assert response.status_code == 201
    assert response.json()["data"][0]["id"] == str(ev_id)


@patch("app.schematization.router.add_evidence")
@patch("app.schematization.router.get_db")
def test_add_evidence_with_parent(mock_db, mock_add, client):
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    frame_id = uuid.uuid4()
    mock_add.return_value = _make_schema(
        ws_id,
        [{"type": "frame", "id": str(frame_id), "children": [
            {"type": "evidence", "id": str(ev_id), "rel": "question"},
        ]}],
    )
    response = client.post(
        f"/api/workspaces/{ws_id}/schematization/evidence",
        json={
            "evidence_id": str(ev_id),
            "parent_id": str(frame_id),
            "index": 0,
            "rel": "question",
        },
    )
    assert response.status_code == 201
    mock_add.assert_called_once()
    call_kwargs = mock_add.call_args
    assert call_kwargs[0][3] == frame_id
    assert call_kwargs[0][4] == 0
    assert call_kwargs[0][5] == "question"


@patch("app.schematization.router.remove_evidence")
@patch("app.schematization.router.get_db")
def test_remove_evidence(mock_db, mock_remove, client):
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    mock_remove.return_value = _make_schema(ws_id)
    response = client.delete(f"/api/workspaces/{ws_id}/schematization/evidence/{ev_id}")
    assert response.status_code == 200
    assert response.json()["data"] == []


@patch("app.schematization.router.create_frame")
@patch("app.schematization.router.get_db")
def test_create_frame(mock_db, mock_create, client):
    ws_id = uuid.uuid4()
    fid = str(uuid.uuid4())
    mock_create.return_value = _make_schema(
        ws_id,
        [{"type": "frame", "id": fid, "title": "H1", "description": "", "children": []}],
    )
    response = client.post(
        f"/api/workspaces/{ws_id}/schematization/frames",
        json={"title": "H1"},
    )
    assert response.status_code == 201
    assert response.json()["data"][0]["title"] == "H1"


@patch("app.schematization.router.update_frame")
@patch("app.schematization.router.get_db")
def test_update_frame(mock_db, mock_update, client):
    ws_id = uuid.uuid4()
    fid = uuid.uuid4()
    mock_update.return_value = _make_schema(
        ws_id,
        [{"type": "frame", "id": str(fid), "title": "Updated", "description": "d", "children": []}],
    )
    response = client.patch(
        f"/api/workspaces/{ws_id}/schematization/frames/{fid}",
        json={"title": "Updated", "description": "d"},
    )
    assert response.status_code == 200
    assert response.json()["data"][0]["title"] == "Updated"


@patch("app.schematization.router.remove_node")
@patch("app.schematization.router.get_db")
def test_remove_frame(mock_db, mock_remove, client):
    ws_id = uuid.uuid4()
    fid = uuid.uuid4()
    mock_remove.return_value = _make_schema(ws_id)
    response = client.delete(f"/api/workspaces/{ws_id}/schematization/frames/{fid}")
    assert response.status_code == 200


@patch("app.schematization.router.move_node")
@patch("app.schematization.router.get_db")
def test_move_node(mock_db, mock_move, client):
    ws_id = uuid.uuid4()
    node_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    mock_move.return_value = _make_schema(ws_id, [])
    response = client.post(
        f"/api/workspaces/{ws_id}/schematization/nodes/{node_id}/move",
        json={"parent_id": str(parent_id), "index": 0, "rel": "cancel"},
    )
    assert response.status_code == 200
    mock_move.assert_called_once()
