import uuid
from unittest.mock import MagicMock

from app.schematization.service import add_evidence, get_or_create, remove_evidence


def test_get_or_create_existing():
    db = MagicMock()
    ws_id = uuid.uuid4()
    existing = MagicMock()
    db.get.return_value = existing
    result = get_or_create(db, ws_id)
    assert result is existing
    db.add.assert_not_called()


def test_get_or_create_new():
    db = MagicMock()
    ws_id = uuid.uuid4()
    db.get.return_value = None
    result = get_or_create(db, ws_id)
    assert result.workspace_id == ws_id
    assert result.data == {"frames": [], "evidence": [], "relationships": []}
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_add_evidence():
    db = MagicMock()
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = {"frames": [], "evidence": [], "relationships": []}
    db.get.return_value = existing
    result = add_evidence(db, ws_id, ev_id)
    assert str(ev_id) in result.data["evidence"]
    db.commit.assert_called_once()


def test_add_evidence_idempotent():
    db = MagicMock()
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = {"frames": [], "evidence": [str(ev_id)], "relationships": []}
    db.get.return_value = existing
    add_evidence(db, ws_id, ev_id)
    assert existing.data["evidence"].count(str(ev_id)) == 1


def test_remove_evidence():
    db = MagicMock()
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = {"frames": [], "evidence": [str(ev_id)], "relationships": []}
    db.get.return_value = existing
    result = remove_evidence(db, ws_id, ev_id)
    assert str(ev_id) not in result.data["evidence"]
    db.commit.assert_called_once()


def test_remove_evidence_not_present():
    db = MagicMock()
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = {"frames": [], "evidence": [], "relationships": []}
    db.get.return_value = existing
    result = remove_evidence(db, ws_id, ev_id)
    assert result.data["evidence"] == []
