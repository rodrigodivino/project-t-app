import uuid

from sqlalchemy.orm import Session

from app.shoebox.models import ShoeboxItem


def list_items(db: Session, workspace_id: uuid.UUID) -> list[ShoeboxItem]:
    return list(
        db.query(ShoeboxItem)
        .filter(ShoeboxItem.workspace_id == workspace_id)
        .order_by(ShoeboxItem.added_at.desc())
        .all()
    )


def add_item(
    db: Session, workspace_id: uuid.UUID, source_document_id: uuid.UUID
) -> ShoeboxItem:
    item = ShoeboxItem(
        workspace_id=workspace_id,
        source_document_id=source_document_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_item(
    db: Session, workspace_id: uuid.UUID, source_document_id: uuid.UUID
) -> bool:
    item = (
        db.query(ShoeboxItem)
        .filter(
            ShoeboxItem.workspace_id == workspace_id,
            ShoeboxItem.source_document_id == source_document_id,
        )
        .first()
    )
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True
