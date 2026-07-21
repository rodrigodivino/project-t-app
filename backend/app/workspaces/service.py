import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.evidence.service import add_item as add_evidence
from app.shoebox.service import add_item as add_shoebox
from app.sources.service import execute_query
from app.workspaces.models import Workspace

DEFAULT_QUERY = "SELECT * FROM post_rede_social_himark WHERE time >= '2020-04-06 00:00' AND time < '2020-04-06 01:00'"


def create_workspace(db: Session, name: str) -> Workspace:
    ws = Workspace(name=name)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    _seed_workspace(db, ws.id)
    return ws


def _serialize_row(row: dict) -> dict:
    return {
        k: v.isoformat() if isinstance(v, (datetime, date)) else v
        for k, v in row.items()
    }


def _seed_workspace(db: Session, ws_id: uuid.UUID) -> None:
    rows = [_serialize_row(r) for r in execute_query(db, DEFAULT_QUERY)]
    if not rows:
        return
    shoebox = add_shoebox(db, ws_id, DEFAULT_QUERY, "Consulta inicial", rows)
    add_evidence(db, ws_id, shoebox.id, "Relatos de danos estruturais aumentam ao longo do período", [1, 3], ai_authored=True)
    add_evidence(db, ws_id, shoebox.id, "Moradores pedem ajuda com alagamento", [0, 2], ai_authored=False)


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
