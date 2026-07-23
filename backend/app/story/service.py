import uuid

from sqlalchemy.orm import Session

from app.story.models import Story


def get_or_create(db: Session, workspace_id: uuid.UUID) -> Story:
    row = db.get(Story, workspace_id)
    if row is not None:
        return row
    row = Story(workspace_id=workspace_id, content="")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_content(db: Session, workspace_id: uuid.UUID, content: str) -> Story:
    row = get_or_create(db, workspace_id)
    row.content = content
    db.commit()
    db.refresh(row)
    return row
