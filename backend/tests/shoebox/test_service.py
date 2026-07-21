import uuid
from unittest.mock import MagicMock

from app.shoebox.service import add_item, get_item, list_items, remove_item


def test_add_item():
    db = MagicMock()
    ws_id = uuid.uuid4()
    item = add_item(
        db, ws_id, "SELECT * FROM post_rede_social_himark", "test explanation", [{"a": 1}]
    )
    db.add.assert_called_once_with(item)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(item)
    assert item.workspace_id == ws_id
    assert item.query == "SELECT * FROM post_rede_social_himark"
    assert item.explanation == "test explanation"
    assert item.result == [{"a": 1}]
    assert item.ai_authored is False


def test_add_item_ai_authored():
    db = MagicMock()
    ws_id = uuid.uuid4()
    item = add_item(
        db, ws_id, "SELECT * FROM post_rede_social_himark", "AI query", [{}],
        ai_authored=True,
    )
    assert item.ai_authored is True


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
