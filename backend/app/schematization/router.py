import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependency import require_auth
from app.database import get_db
from app.schematization.service import add_evidence, get_or_create, remove_evidence, trigger_search

router = APIRouter(
    prefix="/api/workspaces/{ws_id}/schematization",
    tags=["schematization"],
    dependencies=[Depends(require_auth)],
)


class SchematizationResponse(BaseModel):
    workspace_id: uuid.UUID
    data: dict

    model_config = {"from_attributes": True}


class AddEvidenceRequest(BaseModel):
    evidence_id: uuid.UUID


@router.get("", response_model=SchematizationResponse)
def get(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> SchematizationResponse:
    row = get_or_create(db, ws_id)
    return SchematizationResponse.model_validate(row)


@router.post("/evidence", response_model=SchematizationResponse, status_code=201)
def add_ev(
    ws_id: uuid.UUID, body: AddEvidenceRequest, db: Session = Depends(get_db)
) -> SchematizationResponse:
    row = add_evidence(db, ws_id, body.evidence_id)
    return SchematizationResponse.model_validate(row)


@router.delete("/evidence/{evidence_id}", response_model=SchematizationResponse)
def remove_ev(
    ws_id: uuid.UUID, evidence_id: uuid.UUID, db: Session = Depends(get_db)
) -> SchematizationResponse:
    row = remove_evidence(db, ws_id, evidence_id)
    return SchematizationResponse.model_validate(row)


@router.post("/ai-search", status_code=202)
def ai_search(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    trigger_search(db, ws_id)
    return {"status": "accepted"}
