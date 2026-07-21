import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependency import require_auth
from app.database import get_db
from app.sources.service import (
    delete_document,
    get_document,
    list_documents,
    upload_document,
)

router = APIRouter(
    prefix="/api/workspaces/{ws_id}/sources",
    tags=["sources"],
    dependencies=[Depends(require_auth)],
)


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str

    model_config = {"from_attributes": True}


@router.post("", response_model=DocumentOut, status_code=201)
async def upload(
    ws_id: uuid.UUID, file: UploadFile, db: Session = Depends(get_db)
) -> DocumentOut:
    content = await file.read()
    doc = upload_document(
        db,
        workspace_id=ws_id,
        filename=file.filename or "untitled.md",
        content=content,
        content_type="text/markdown",
    )
    return DocumentOut.model_validate(doc)


@router.get("", response_model=list[DocumentOut])
def list_all(
    ws_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[DocumentOut]:
    docs = list_documents(db, ws_id)
    return [DocumentOut.model_validate(d) for d in docs]


@router.get("/{doc_id}", response_model=DocumentOut)
def get_one(
    ws_id: uuid.UUID, doc_id: uuid.UUID, db: Session = Depends(get_db)
) -> DocumentOut:
    doc = get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentOut.model_validate(doc)


@router.get("/{doc_id}/content")
def get_content(
    ws_id: uuid.UUID, doc_id: uuid.UUID, db: Session = Depends(get_db)
) -> Response:
    doc = get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(
        content=doc.content,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )


@router.delete("/{doc_id}", status_code=204)
def delete(
    ws_id: uuid.UUID, doc_id: uuid.UUID, db: Session = Depends(get_db)
) -> None:
    if not delete_document(db, doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
