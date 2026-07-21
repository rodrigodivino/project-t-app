import uuid
from unittest.mock import MagicMock

from app.evidence.service import (
    add_item,
    approve_item,
    correct_item,
    get_item,
    list_items,
    reject_item,
    remove_item,
)


def test_add_item():
    db = MagicMock()
    ws_id = uuid.uuid4()
    shoebox_id = uuid.uuid4()
    item = add_item(db, ws_id, shoebox_id, "district shows rising damage reports", [0, 2])
    db.add.assert_called_once_with(item)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(item)
    assert item.workspace_id == ws_id
    assert item.shoebox_id == shoebox_id
    assert item.content == "district shows rising damage reports"
    assert item.rows == [0, 2]
    assert item.ai_authored is False


def test_add_item_ai_authored():
    db = MagicMock()
    ws_id = uuid.uuid4()
    shoebox_id = uuid.uuid4()
    item = add_item(db, ws_id, shoebox_id, "AI snippet", [1], ai_authored=True)
    assert item.ai_authored is True


def test_correct_item():
    db = MagicMock()
    item_id = uuid.uuid4()
    fake_item = MagicMock()
    fake_item.ai_authored = True
    db.get.return_value = fake_item
    result = correct_item(db, item_id, "corrected text")
    assert result is fake_item
    assert fake_item.content == "corrected text"
    assert fake_item.ai_authored is False
    assert fake_item.approved is False
    db.commit.assert_called_once()


def test_correct_item_not_found():
    db = MagicMock()
    db.get.return_value = None
    assert correct_item(db, uuid.uuid4(), "text") is None


def test_approve_item():
    db = MagicMock()
    item_id = uuid.uuid4()
    fake_item = MagicMock()
    fake_item.approved = False
    db.get.return_value = fake_item
    result = approve_item(db, item_id)
    assert result is fake_item
    assert fake_item.approved is True
    db.commit.assert_called_once()


def test_approve_item_not_found():
    db = MagicMock()
    db.get.return_value = None
    assert approve_item(db, uuid.uuid4()) is None


def test_reject_item():
    db = MagicMock()
    item_id = uuid.uuid4()
    fake_item = MagicMock()
    fake_item.rejected = False
    db.get.return_value = fake_item
    result = reject_item(db, item_id)
    assert result is fake_item
    assert fake_item.rejected is True
    db.commit.assert_called_once()


def test_reject_item_not_found():
    db = MagicMock()
    db.get.return_value = None
    assert reject_item(db, uuid.uuid4()) is None


def test_list_items():
    db = MagicMock()
    ws_id = uuid.uuid4()
    list_items(db, ws_id)
    db.query.assert_called_once()


def test_get_item():
    db = MagicMock()
    item_id = uuid.uuid4()
    get_item(db, item_id)
    db.get.assert_called_once()


def test_remove_item_found():
    db = MagicMock()
    item_id = uuid.uuid4()
    fake_item = MagicMock()
    db.get.return_value = fake_item
    assert remove_item(db, item_id) is True
    db.delete.assert_called_once_with(fake_item)
    db.commit.assert_called_once()


def test_remove_item_not_found():
    db = MagicMock()
    item_id = uuid.uuid4()
    db.get.return_value = None
    assert remove_item(db, item_id) is False
    db.delete.assert_not_called()
