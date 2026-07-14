import uuid
from unittest.mock import MagicMock

from app.workspaces.models import Workspace
from app.workspaces.service import (
    create_workspace,
    delete_workspace,
    get_workspace,
    list_workspaces,
)


def _make_ws(**overrides):
    defaults = {"id": uuid.uuid4(), "name": "My workspace"}
    defaults.update(overrides)
    ws = MagicMock(spec=Workspace)
    for k, v in defaults.items():
        setattr(ws, k, v)
    return ws


def test_create_workspace():
    db = MagicMock()
    ws = create_workspace(db, "Test")
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
    assert ws.name == "Test"


def test_list_workspaces():
    db = MagicMock()
    items = [_make_ws(), _make_ws(name="Other")]
    db.query.return_value.order_by.return_value.all.return_value = items
    result = list_workspaces(db)
    assert len(result) == 2


def test_get_workspace_found():
    db = MagicMock()
    ws = _make_ws()
    db.get.return_value = ws
    assert get_workspace(db, ws.id) is ws


def test_get_workspace_not_found():
    db = MagicMock()
    db.get.return_value = None
    assert get_workspace(db, uuid.uuid4()) is None


def test_delete_workspace_found():
    db = MagicMock()
    ws = _make_ws()
    db.get.return_value = ws
    assert delete_workspace(db, ws.id) is True
    db.delete.assert_called_once_with(ws)
    db.commit.assert_called_once()


def test_delete_workspace_not_found():
    db = MagicMock()
    db.get.return_value = None
    assert delete_workspace(db, uuid.uuid4()) is False
    db.delete.assert_not_called()
