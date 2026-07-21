import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependency import require_auth
from app.database import get_db
from app.shoebox.service import (
    add_item,
    get_filename,
    get_source_for_item,
    list_items,
    remove_item,
)

router = APIRouter(
    prefix="/api/workspaces/{ws_id}/shoebox",
    tags=["shoebox"],
    dependencies=[Depends(require_auth)],
)


class ShoeboxItemOut(BaseModel):
    id: uuid.UUID
    source_document_id: uuid.UUID
    filename: str

    model_config = {"from_attributes": True}


class ShoeboxAddRequest(BaseModel):
    source_document_id: uuid.UUID


@router.get("", response_model=list[ShoeboxItemOut])
def list_all(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ShoeboxItemOut]:
    items = list_items(db, ws_id)
    return [
        ShoeboxItemOut(
            id=i.id,
            source_document_id=i.source_document_id,
            filename=get_filename(db, i.source_document_id),
        )
        for i in items
    ]


@router.post("", response_model=ShoeboxItemOut, status_code=201)
def add(
    ws_id: uuid.UUID, body: ShoeboxAddRequest, db: Session = Depends(get_db)
) -> ShoeboxItemOut:
    try:
        item = add_item(db, ws_id, body.source_document_id)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Already in shoebox")
    return ShoeboxItemOut(
        id=item.id,
        source_document_id=item.source_document_id,
        filename=get_filename(db, item.source_document_id),
    )


@router.get("/{doc_id}/content")
def get_content(
    ws_id: uuid.UUID, doc_id: uuid.UUID, db: Session = Depends(get_db)
) -> Response:
    doc = get_source_for_item(db, ws_id, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Not in shoebox")
    return Response(
        content=doc.content,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )


@router.delete("/{doc_id}", status_code=204)
def remove(ws_id: uuid.UUID, doc_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not remove_item(db, ws_id, doc_id):
        raise HTTPException(status_code=404, detail="Not in shoebox")
