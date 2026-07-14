import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependency import require_auth
from app.database import get_db
from app.shoebox.service import add_item, list_items, remove_item

router = APIRouter(
    prefix="/api/workspaces/{ws_id}/shoebox",
    tags=["shoebox"],
    dependencies=[Depends(require_auth)],
)


class ShoeboxItemOut(BaseModel):
    id: uuid.UUID
    source_document_id: uuid.UUID

    model_config = {"from_attributes": True}


class ShoeboxAddRequest(BaseModel):
    source_document_id: uuid.UUID


@router.get("", response_model=list[ShoeboxItemOut])
def list_all(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ShoeboxItemOut]:
    items = list_items(db, ws_id)
    return [ShoeboxItemOut.model_validate(i) for i in items]


@router.post("", response_model=ShoeboxItemOut, status_code=201)
def add(
    ws_id: uuid.UUID, body: ShoeboxAddRequest, db: Session = Depends(get_db)
) -> ShoeboxItemOut:
    try:
        item = add_item(db, ws_id, body.source_document_id)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Already in shoebox")
    return ShoeboxItemOut.model_validate(item)


@router.delete("/{doc_id}", status_code=204)
def remove(ws_id: uuid.UUID, doc_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not remove_item(db, ws_id, doc_id):
        raise HTTPException(status_code=404, detail="Not in shoebox")
