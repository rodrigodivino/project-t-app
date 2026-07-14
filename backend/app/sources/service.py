import uuid

from sqlalchemy.orm import Session

from app.sources.models import SourceDocument


def upload_document(
    db: Session,
    workspace_id: uuid.UUID,
    filename: str,
    content: bytes,
    content_type: str,
) -> SourceDocument:
    doc = SourceDocument(
        workspace_id=workspace_id,
        filename=filename,
        content=content,
        content_type=content_type,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def list_documents(db: Session, workspace_id: uuid.UUID) -> list[SourceDocument]:
    return list(
        db.query(SourceDocument)
        .filter(SourceDocument.workspace_id == workspace_id)
        .order_by(SourceDocument.uploaded_at.desc())
        .all()
    )


def get_document(db: Session, doc_id: uuid.UUID) -> SourceDocument | None:
    return db.get(SourceDocument, doc_id)


def delete_document(db: Session, doc_id: uuid.UUID) -> bool:
    doc = db.get(SourceDocument, doc_id)
    if doc is None:
        return False
    db.delete(doc)
    db.commit()
    return True
