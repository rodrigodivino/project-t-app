import uuid

from sqlalchemy.orm import Session

from app.ai import read_and_extract, search_and_query
from app.schematization.models import Schematization
from app import settings

EMPTY_DATA: dict = {"frames": [], "evidence": [], "relationships": []}


def get_or_create(db: Session, workspace_id: uuid.UUID) -> Schematization:
    row = db.get(Schematization, workspace_id)
    if row is not None:
        return row
    row = Schematization(workspace_id=workspace_id, data=dict(EMPTY_DATA))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def add_evidence(db: Session, workspace_id: uuid.UUID, evidence_id: uuid.UUID) -> Schematization:
    row = get_or_create(db, workspace_id)
    eid = str(evidence_id)
    data: dict = dict(row.data)
    ids: list[str] = list(data.get("evidence", []))
    if eid not in ids:
        ids.append(eid)
    data["evidence"] = ids
    row.data = data
    db.commit()
    db.refresh(row)
    _maybe_fire(workspace_id, row.data)
    return row


def remove_evidence(db: Session, workspace_id: uuid.UUID, evidence_id: uuid.UUID) -> Schematization:
    row = get_or_create(db, workspace_id)
    eid = str(evidence_id)
    data: dict = dict(row.data)
    ids: list[str] = list(data.get("evidence", []))
    ids = [i for i in ids if i != eid]
    data["evidence"] = ids
    row.data = data
    db.commit()
    db.refresh(row)
    _maybe_fire(workspace_id, row.data)
    return row


def trigger_search(db: Session, workspace_id: uuid.UUID) -> None:
    if not settings.ANTHROPIC_API_KEY:
        return
    row = get_or_create(db, workspace_id)
    search_and_query.fire(workspace_id, row.data)


def _maybe_fire(workspace_id: uuid.UUID, data: dict) -> None:
    if not settings.ANTHROPIC_API_KEY:
        return
    if not data.get("evidence"):
        return
    search_and_query.fire(workspace_id, data)
    read_and_extract.fire(workspace_id)
