import uuid
from unittest.mock import MagicMock, patch

from app.schematization.models import Schematization


def _make_schema(ws_id=None, data=None):
    ws_id = ws_id or uuid.uuid4()
    data = data or {"frames": [], "evidence": [], "relationships": []}
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
    assert response.json()["data"]["evidence"] == []


@patch("app.schematization.router.add_evidence")
@patch("app.schematization.router.get_db")
def test_add_evidence(mock_db, mock_add, client):
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    mock_add.return_value = _make_schema(ws_id, {"frames": [], "evidence": [str(ev_id)], "relationships": []})
    response = client.post(
        f"/api/workspaces/{ws_id}/schematization/evidence",
        json={"evidence_id": str(ev_id)},
    )
    assert response.status_code == 201
    assert str(ev_id) in response.json()["data"]["evidence"]


@patch("app.schematization.router.remove_evidence")
@patch("app.schematization.router.get_db")
def test_remove_evidence(mock_db, mock_remove, client):
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    mock_remove.return_value = _make_schema(ws_id)
    response = client.delete(f"/api/workspaces/{ws_id}/schematization/evidence/{ev_id}")
    assert response.status_code == 200
    assert response.json()["data"]["evidence"] == []
