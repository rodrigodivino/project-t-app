import uuid
from unittest.mock import MagicMock

from app.sources.models import SourceDocument
from app.sources.service import (
    delete_document,
    get_document,
    list_documents,
    upload_document,
)


def _make_doc(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "workspace_id": uuid.uuid4(),
        "filename": "test.md",
        "content": b"# Hello",
        "content_type": "text/markdown",
    }
    defaults.update(overrides)
    doc = MagicMock(spec=SourceDocument)
    for k, v in defaults.items():
        setattr(doc, k, v)
    return doc


def test_upload_document():
    db = MagicMock()
    ws_id = uuid.uuid4()
    doc = upload_document(db, ws_id, "report.md", b"# data", "text/markdown")
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
    assert doc.filename == "report.md"
    assert doc.workspace_id == ws_id


def test_list_documents():
    db = MagicMock()
    ws_id = uuid.uuid4()
    docs = [_make_doc(), _make_doc(filename="other.md")]
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
        docs
    )
    result = list_documents(db, ws_id)
    assert len(result) == 2


def test_get_document_found():
    db = MagicMock()
    doc = _make_doc()
    db.get.return_value = doc
    assert get_document(db, doc.id) is doc


def test_get_document_not_found():
    db = MagicMock()
    db.get.return_value = None
    assert get_document(db, uuid.uuid4()) is None


def test_delete_document_found():
    db = MagicMock()
    doc = _make_doc()
    db.get.return_value = doc
    assert delete_document(db, doc.id) is True
    db.delete.assert_called_once_with(doc)
    db.commit.assert_called_once()


def test_delete_document_not_found():
    db = MagicMock()
    db.get.return_value = None
    assert delete_document(db, uuid.uuid4()) is False
    db.delete.assert_not_called()
