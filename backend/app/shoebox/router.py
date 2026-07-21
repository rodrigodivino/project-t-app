import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependency import require_auth
from app.database import get_db
from app.shoebox.service import add_item, get_item, list_items, remove_item

router = APIRouter(
    prefix="/api/workspaces/{ws_id}/shoebox",
    tags=["shoebox"],
    dependencies=[Depends(require_auth)],
)


class ShoeboxItemSummary(BaseModel):
    id: uuid.UUID
    query: str
    explanation: str
    ai_authored: bool
    added_at: datetime

    model_config = {"from_attributes": True}


class ShoeboxItemFull(BaseModel):
    id: uuid.UUID
    query: str
    explanation: str
    result: list[dict]
    ai_authored: bool
    added_at: datetime

    model_config = {"from_attributes": True}


class ShoeboxAddRequest(BaseModel):
    query: str
    explanation: str
    result: list[dict]


@router.get("", response_model=list[ShoeboxItemSummary])
def list_all(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ShoeboxItemSummary]:
    items = list_items(db, ws_id)
    return [ShoeboxItemSummary.model_validate(i) for i in items]


@router.post("", response_model=ShoeboxItemFull, status_code=201)
def add(
    ws_id: uuid.UUID, body: ShoeboxAddRequest, db: Session = Depends(get_db)
) -> ShoeboxItemFull:
    item = add_item(db, ws_id, body.query, body.explanation, body.result)
    return ShoeboxItemFull.model_validate(item)


@router.get("/{item_id}", response_model=ShoeboxItemFull)
def get_one(
    ws_id: uuid.UUID, item_id: uuid.UUID, db: Session = Depends(get_db)
) -> ShoeboxItemFull:
    item = get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return ShoeboxItemFull.model_validate(item)


@router.delete("/{item_id}", status_code=204)
def remove(ws_id: uuid.UUID, item_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not remove_item(db, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
