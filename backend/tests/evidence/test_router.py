import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.evidence.models import EvidenceItem


def _make_item(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "workspace_id": uuid.uuid4(),
        "shoebox_id": uuid.uuid4(),
        "content": "district shows rising damage reports",
        "rows": [0, 2],
        "ai_authored": False,
        "approved": False,
        "rejected": False,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    item = MagicMock(spec=EvidenceItem)
    for k, v in defaults.items():
        setattr(item, k, v)
    return item


@patch("app.evidence.router.list_items")
@patch("app.evidence.router.get_db")
def test_list_evidence(mock_db, mock_list, client):
    ws_id = uuid.uuid4()
    items = [_make_item(workspace_id=ws_id), _make_item(workspace_id=ws_id)]
    mock_list.return_value = items
    response = client.get(f"/api/workspaces/{ws_id}/evidence")
    assert response.status_code == 200
    assert len(response.json()) == 2


@patch("app.evidence.router.add_item")
@patch("app.evidence.router.get_db")
def test_add_evidence(mock_db, mock_add, client):
    ws_id = uuid.uuid4()
    shoebox_id = uuid.uuid4()
    item = _make_item(workspace_id=ws_id, shoebox_id=shoebox_id)
    mock_add.return_value = item
    response = client.post(
        f"/api/workspaces/{ws_id}/evidence",
        json={
            "shoebox_id": str(shoebox_id),
            "content": "district shows rising damage reports",
            "rows": [0, 2],
        },
    )
    assert response.status_code == 201
    assert response.json()["content"] == "district shows rising damage reports"


@patch("app.evidence.router.get_item")
@patch("app.evidence.router.get_db")
def test_get_evidence_item(mock_db, mock_get, client):
    ws_id = uuid.uuid4()
    item_id = uuid.uuid4()
    item = _make_item(id=item_id, workspace_id=ws_id)
    mock_get.return_value = item
    response = client.get(f"/api/workspaces/{ws_id}/evidence/{item_id}")
    assert response.status_code == 200
    assert response.json()["content"] == "district shows rising damage reports"


@patch("app.evidence.router.get_item")
@patch("app.evidence.router.get_db")
def test_get_evidence_item_not_found(mock_db, mock_get, client):
    ws_id = uuid.uuid4()
    mock_get.return_value = None
    response = client.get(f"/api/workspaces/{ws_id}/evidence/{uuid.uuid4()}")
    assert response.status_code == 404


@patch("app.evidence.router.correct_item")
@patch("app.evidence.router.get_db")
def test_correct_evidence(mock_db, mock_correct, client):
    ws_id = uuid.uuid4()
    item_id = uuid.uuid4()
    item = _make_item(id=item_id, ai_authored=False)
    mock_correct.return_value = item
    response = client.patch(
        f"/api/workspaces/{ws_id}/evidence/{item_id}/correct",
        json={"content": "corrected text"},
    )
    assert response.status_code == 200
    mock_correct.assert_called_once()


@patch("app.evidence.router.correct_item")
@patch("app.evidence.router.get_db")
def test_correct_evidence_not_found(mock_db, mock_correct, client):
    ws_id = uuid.uuid4()
    mock_correct.return_value = None
    response = client.patch(
        f"/api/workspaces/{ws_id}/evidence/{uuid.uuid4()}/correct",
        json={"content": "text"},
    )
    assert response.status_code == 404


@patch("app.evidence.router.approve_item")
@patch("app.evidence.router.get_db")
def test_approve_evidence(mock_db, mock_approve, client):
    ws_id = uuid.uuid4()
    item_id = uuid.uuid4()
    item = _make_item(id=item_id, approved=True)
    mock_approve.return_value = item
    response = client.patch(f"/api/workspaces/{ws_id}/evidence/{item_id}/approve")
    assert response.status_code == 200
    assert response.json()["approved"] is True


@patch("app.evidence.router.approve_item")
@patch("app.evidence.router.get_db")
def test_approve_evidence_not_found(mock_db, mock_approve, client):
    ws_id = uuid.uuid4()
    mock_approve.return_value = None
    response = client.patch(f"/api/workspaces/{ws_id}/evidence/{uuid.uuid4()}/approve")
    assert response.status_code == 404


@patch("app.evidence.router.reject_item")
@patch("app.evidence.router.get_db")
def test_reject_evidence(mock_db, mock_reject, client):
    ws_id = uuid.uuid4()
    item_id = uuid.uuid4()
    item = _make_item(id=item_id, rejected=True)
    mock_reject.return_value = item
    response = client.patch(f"/api/workspaces/{ws_id}/evidence/{item_id}/reject")
    assert response.status_code == 200
    assert response.json()["rejected"] is True


@patch("app.evidence.router.reject_item")
@patch("app.evidence.router.get_db")
def test_reject_evidence_not_found(mock_db, mock_reject, client):
    ws_id = uuid.uuid4()
    mock_reject.return_value = None
    response = client.patch(f"/api/workspaces/{ws_id}/evidence/{uuid.uuid4()}/reject")
    assert response.status_code == 404


@patch("app.evidence.router.remove_item")
@patch("app.evidence.router.get_db")
def test_remove_evidence(mock_db, mock_remove, client):
    ws_id = uuid.uuid4()
    mock_remove.return_value = True
    response = client.delete(f"/api/workspaces/{ws_id}/evidence/{uuid.uuid4()}")
    assert response.status_code == 204


@patch("app.evidence.router.remove_item")
@patch("app.evidence.router.get_db")
def test_remove_evidence_not_found(mock_db, mock_remove, client):
    ws_id = uuid.uuid4()
    mock_remove.return_value = False
    response = client.delete(f"/api/workspaces/{ws_id}/evidence/{uuid.uuid4()}")
    assert response.status_code == 404
