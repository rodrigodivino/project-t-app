import uuid

from sqlalchemy.orm import Session

from app.evidence.models import EvidenceItem


def list_items(db: Session, workspace_id: uuid.UUID) -> list[EvidenceItem]:
    return list(
        db.query(EvidenceItem)
        .filter(EvidenceItem.workspace_id == workspace_id)
        .filter(EvidenceItem.rejected == False)  # noqa: E712
        .order_by(EvidenceItem.created_at.desc())
        .all()
    )


def get_item(db: Session, item_id: uuid.UUID) -> EvidenceItem | None:
    return db.get(EvidenceItem, item_id)


def add_item(
    db: Session,
    workspace_id: uuid.UUID,
    shoebox_id: uuid.UUID,
    content: str,
    rows: list[int],
    ai_authored: bool = False,
) -> EvidenceItem:
    item = EvidenceItem(
        workspace_id=workspace_id,
        shoebox_id=shoebox_id,
        content=content,
        rows=rows,
        ai_authored=ai_authored,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def correct_item(db: Session, item_id: uuid.UUID, content: str) -> EvidenceItem | None:
    item = db.get(EvidenceItem, item_id)
    if item is None:
        return None
    item.content = content
    item.ai_authored = False
    item.approved = False
    db.commit()
    db.refresh(item)
    return item


def approve_item(db: Session, item_id: uuid.UUID) -> EvidenceItem | None:
    item = db.get(EvidenceItem, item_id)
    if item is None:
        return None
    item.approved = True
    db.commit()
    db.refresh(item)
    return item


def reject_item(db: Session, item_id: uuid.UUID) -> EvidenceItem | None:
    item = db.get(EvidenceItem, item_id)
    if item is None:
        return None
    item.rejected = True
    db.commit()
    db.refresh(item)
    return item


def _xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def serialize_xml(items: list[EvidenceItem]) -> str:
    if not items:
        return "<evidence-file/>"
    lines = ["<evidence-file>"]
    for item in items:
        lines.append(f'<evidence id="{item.id}">{_xml_escape(item.content)}</evidence>')
    lines.append("</evidence-file>")
    return "\n".join(lines)


def remove_item(db: Session, item_id: uuid.UUID) -> bool:
    item = db.get(EvidenceItem, item_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True
