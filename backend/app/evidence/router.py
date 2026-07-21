import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependency import require_auth
from app.database import get_db
from app.evidence.service import (
    add_item,
    approve_item,
    correct_item,
    get_item,
    list_items,
    reject_item,
    remove_item,
)

router = APIRouter(
    prefix="/api/workspaces/{ws_id}/evidence",
    tags=["evidence"],
    dependencies=[Depends(require_auth)],
)


class EvidenceItemSummary(BaseModel):
    id: uuid.UUID
    shoebox_id: uuid.UUID
    content: str
    ai_authored: bool
    approved: bool
    rejected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceItemFull(BaseModel):
    id: uuid.UUID
    shoebox_id: uuid.UUID
    content: str
    rows: list[int]
    ai_authored: bool
    approved: bool
    rejected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceAddRequest(BaseModel):
    shoebox_id: uuid.UUID
    content: str
    rows: list[int]
    ai_authored: bool = False


class EvidenceUpdateRequest(BaseModel):
    content: str


@router.get("", response_model=list[EvidenceItemSummary])
def list_all(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> list[EvidenceItemSummary]:
    items = list_items(db, ws_id)
    return [EvidenceItemSummary.model_validate(i) for i in items]


@router.post("", response_model=EvidenceItemFull, status_code=201)
def add(
    ws_id: uuid.UUID, body: EvidenceAddRequest, db: Session = Depends(get_db)
) -> EvidenceItemFull:
    item = add_item(db, ws_id, body.shoebox_id, body.content, body.rows, body.ai_authored)
    return EvidenceItemFull.model_validate(item)


@router.get("/{item_id}", response_model=EvidenceItemFull)
def get_one(
    ws_id: uuid.UUID, item_id: uuid.UUID, db: Session = Depends(get_db)
) -> EvidenceItemFull:
    item = get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return EvidenceItemFull.model_validate(item)


@router.patch("/{item_id}/correct", response_model=EvidenceItemFull)
def correct(
    ws_id: uuid.UUID,
    item_id: uuid.UUID,
    body: EvidenceUpdateRequest,
    db: Session = Depends(get_db),
) -> EvidenceItemFull:
    item = correct_item(db, item_id, body.content)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return EvidenceItemFull.model_validate(item)


@router.patch("/{item_id}/approve", response_model=EvidenceItemFull)
def approve(
    ws_id: uuid.UUID, item_id: uuid.UUID, db: Session = Depends(get_db)
) -> EvidenceItemFull:
    item = approve_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return EvidenceItemFull.model_validate(item)


@router.patch("/{item_id}/reject", response_model=EvidenceItemFull)
def reject(
    ws_id: uuid.UUID, item_id: uuid.UUID, db: Session = Depends(get_db)
) -> EvidenceItemFull:
    item = reject_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return EvidenceItemFull.model_validate(item)


@router.delete("/{item_id}", status_code=204)
def remove(ws_id: uuid.UUID, item_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not remove_item(db, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
