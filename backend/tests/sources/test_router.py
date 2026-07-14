import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.sources.models import SourceDocument

WS_ID = uuid.uuid4()


def _make_doc(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "workspace_id": WS_ID,
        "filename": "test.pdf",
        "content": b"fake-pdf-bytes",
        "content_type": "application/pdf",
        "uploaded_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    doc = MagicMock(spec=SourceDocument)
    for k, v in defaults.items():
        setattr(doc, k, v)
    return doc


@patch("app.sources.router.list_documents")
@patch("app.sources.router.get_db")
def test_list_sources(mock_db, mock_list, client):
    docs = [_make_doc(filename="a.pdf"), _make_doc(filename="b.pdf")]
    mock_list.return_value = docs
    response = client.get(f"/api/workspaces/{WS_ID}/sources")
    assert response.status_code == 200
    assert len(response.json()) == 2


@patch("app.sources.router.upload_document")
@patch("app.sources.router.get_db")
def test_upload_source(mock_db, mock_upload, client):
    doc = _make_doc(filename="report.pdf")
    mock_upload.return_value = doc
    response = client.post(
        f"/api/workspaces/{WS_ID}/sources",
        files={"file": ("report.pdf", b"fake-content", "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["filename"] == "report.pdf"


@patch("app.sources.router.get_document")
@patch("app.sources.router.get_db")
def test_get_source_found(mock_db, mock_get, client):
    doc = _make_doc()
    mock_get.return_value = doc
    response = client.get(f"/api/workspaces/{WS_ID}/sources/{doc.id}")
    assert response.status_code == 200


@patch("app.sources.router.get_document")
@patch("app.sources.router.get_db")
def test_get_source_not_found(mock_db, mock_get, client):
    mock_get.return_value = None
    response = client.get(f"/api/workspaces/{WS_ID}/sources/{uuid.uuid4()}")
    assert response.status_code == 404


@patch("app.sources.router.delete_document")
@patch("app.sources.router.get_db")
def test_delete_source(mock_db, mock_delete, client):
    mock_delete.return_value = True
    response = client.delete(f"/api/workspaces/{WS_ID}/sources/{uuid.uuid4()}")
    assert response.status_code == 204


@patch("app.sources.router.delete_document")
@patch("app.sources.router.get_db")
def test_delete_source_not_found(mock_db, mock_delete, client):
    mock_delete.return_value = False
    response = client.delete(f"/api/workspaces/{WS_ID}/sources/{uuid.uuid4()}")
    assert response.status_code == 404
