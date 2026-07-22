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


def get_item(db: Session, item_id: uuid.UUID) -> ShoeboxItem | None:
    return db.get(ShoeboxItem, item_id)


def add_item(
    db: Session,
    workspace_id: uuid.UUID,
    query: str,
    explanation: str,
    result: list[dict],
    ai_authored: bool = False,
    chart_spec: dict | None = None,
) -> ShoeboxItem:
    item = ShoeboxItem(
        workspace_id=workspace_id,
        query=query,
        explanation=explanation,
        result=result,
        chart_spec=chart_spec,
        ai_authored=ai_authored,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_summaries_for_prompt(
    db: Session, workspace_id: uuid.UUID, max_sample_rows: int = 10,
) -> list[dict]:
    items = list_items(db, workspace_id)
    return [
        {
            "query": item.query,
            "explanation": item.explanation,
            "sample_rows": item.result[:max_sample_rows],
        }
        for item in items
    ]


def remove_item(db: Session, item_id: uuid.UUID) -> bool:
    item = db.get(ShoeboxItem, item_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True
