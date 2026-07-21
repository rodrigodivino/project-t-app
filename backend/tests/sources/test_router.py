import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.sources.models import SourceDocument

WS_ID = uuid.uuid4()


def _make_doc(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "workspace_id": WS_ID,
        "filename": "test.md",
        "content": b"# Hello",
        "content_type": "text/markdown",
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
    docs = [_make_doc(filename="a.md"), _make_doc(filename="b.md")]
    mock_list.return_value = docs
    response = client.get(f"/api/workspaces/{WS_ID}/sources")
    assert response.status_code == 200
    assert len(response.json()) == 2


@patch("app.sources.router.upload_document")
@patch("app.sources.router.get_db")
def test_upload_source(mock_db, mock_upload, client):
    doc = _make_doc(filename="report.md")
    mock_upload.return_value = doc
    response = client.post(
        f"/api/workspaces/{WS_ID}/sources",
        files={"file": ("report.md", b"# Report", "text/markdown")},
    )
    assert response.status_code == 201
    assert response.json()["filename"] == "report.md"


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


@patch("app.sources.router.get_document")
@patch("app.sources.router.get_db")
def test_get_content(mock_db, mock_get, client):
    doc = _make_doc(content=b"# Test content", content_type="text/markdown")
    mock_get.return_value = doc
    response = client.get(f"/api/workspaces/{WS_ID}/sources/{doc.id}/content")
    assert response.status_code == 200
    assert response.content == b"# Test content"
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"


@patch("app.sources.router.get_document")
@patch("app.sources.router.get_db")
def test_get_content_not_found(mock_db, mock_get, client):
    mock_get.return_value = None
    response = client.get(f"/api/workspaces/{WS_ID}/sources/{uuid.uuid4()}/content")
    assert response.status_code == 404
