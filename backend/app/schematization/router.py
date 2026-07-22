import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependency import require_auth
from app.database import get_db
from app.schematization.service import (
    add_evidence,
    create_frame,
    get_or_create,
    move_node,
    remove_evidence,
    remove_node,
    trigger_extract,
    trigger_search,
    update_frame,
)

router = APIRouter(
    prefix="/api/workspaces/{ws_id}/schematization",
    tags=["schematization"],
    dependencies=[Depends(require_auth)],
)


class SchematizationResponse(BaseModel):
    workspace_id: uuid.UUID
    data: list

    model_config = {"from_attributes": True}


class AddEvidenceRequest(BaseModel):
    evidence_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    index: int | None = None
    rel: str = "elaborate"


class CreateFrameRequest(BaseModel):
    title: str
    description: str = ""


class UpdateFrameRequest(BaseModel):
    title: str | None = None
    description: str | None = None


class MoveNodeRequest(BaseModel):
    parent_id: uuid.UUID | None = None
    index: int | None = None
    rel: str = "elaborate"


@router.get("", response_model=SchematizationResponse)
def get(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> SchematizationResponse:
    row = get_or_create(db, ws_id)
    return SchematizationResponse.model_validate(row)


@router.post("/evidence", response_model=SchematizationResponse, status_code=201)
def add_ev(
    ws_id: uuid.UUID, body: AddEvidenceRequest, db: Session = Depends(get_db)
) -> SchematizationResponse:
    try:
        row = add_evidence(
            db, ws_id, body.evidence_id, body.parent_id, body.index, body.rel
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SchematizationResponse.model_validate(row)


@router.delete("/evidence/{evidence_id}", response_model=SchematizationResponse)
def remove_ev(
    ws_id: uuid.UUID, evidence_id: uuid.UUID, db: Session = Depends(get_db)
) -> SchematizationResponse:
    row = remove_evidence(db, ws_id, evidence_id)
    return SchematizationResponse.model_validate(row)


@router.post("/frames", response_model=SchematizationResponse, status_code=201)
def create_fr(
    ws_id: uuid.UUID, body: CreateFrameRequest, db: Session = Depends(get_db)
) -> SchematizationResponse:
    row = create_frame(db, ws_id, body.title, body.description)
    return SchematizationResponse.model_validate(row)


@router.patch("/frames/{frame_id}", response_model=SchematizationResponse)
def update_fr(
    ws_id: uuid.UUID,
    frame_id: uuid.UUID,
    body: UpdateFrameRequest,
    db: Session = Depends(get_db),
) -> SchematizationResponse:
    try:
        row = update_frame(db, ws_id, frame_id, body.title, body.description)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SchematizationResponse.model_validate(row)


@router.delete("/frames/{frame_id}", response_model=SchematizationResponse)
def remove_fr(
    ws_id: uuid.UUID, frame_id: uuid.UUID, db: Session = Depends(get_db)
) -> SchematizationResponse:
    try:
        row = remove_node(db, ws_id, frame_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SchematizationResponse.model_validate(row)


@router.post(
    "/nodes/{node_id}/move", response_model=SchematizationResponse
)
def move_nd(
    ws_id: uuid.UUID,
    node_id: uuid.UUID,
    body: MoveNodeRequest,
    db: Session = Depends(get_db),
) -> SchematizationResponse:
    try:
        row = move_node(db, ws_id, node_id, body.parent_id, body.index, body.rel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SchematizationResponse.model_validate(row)


@router.post("/ai-search", status_code=202)
def ai_search(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    trigger_search(db, ws_id)
    return {"status": "accepted"}


@router.post("/ai-extract", status_code=202)
def ai_extract(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    trigger_extract(db, ws_id)
    return {"status": "accepted"}
