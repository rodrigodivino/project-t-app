import uuid
from unittest.mock import MagicMock

from app.shoebox.service import add_item, list_items, remove_item


def test_add_item():
    db = MagicMock()
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    item = add_item(db, ws_id, doc_id)
    db.add.assert_called_once_with(item)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(item)
    assert item.workspace_id == ws_id
    assert item.source_document_id == doc_id


def test_list_items():
    db = MagicMock()
    ws_id = uuid.uuid4()
    list_items(db, ws_id)
    db.query.assert_called_once()


def test_remove_item_found():
    db = MagicMock()
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    fake_item = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = fake_item
    assert remove_item(db, ws_id, doc_id) is True
    db.delete.assert_called_once_with(fake_item)
    db.commit.assert_called_once()


def test_remove_item_not_found():
    db = MagicMock()
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    db.query.return_value.filter.return_value.first.return_value = None
    assert remove_item(db, ws_id, doc_id) is False
    db.delete.assert_not_called()
