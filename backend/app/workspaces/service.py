import uuid

from sqlalchemy.orm import Session

from app.sources.service import seed_workspace
from app.workspaces.models import Workspace


def create_workspace(db: Session, name: str) -> Workspace:
    ws = Workspace(name=name)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    seed_workspace(db, ws.id)
    return ws


def list_workspaces(db: Session) -> list[Workspace]:
    return list(db.query(Workspace).order_by(Workspace.created_at.desc()).all())


def get_workspace(db: Session, ws_id: uuid.UUID) -> Workspace | None:
    return db.get(Workspace, ws_id)


def delete_workspace(db: Session, ws_id: uuid.UUID) -> bool:
    ws = db.get(Workspace, ws_id)
    if ws is None:
        return False
    db.delete(ws)
    db.commit()
    return True
