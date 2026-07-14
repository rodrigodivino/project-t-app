import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependency import require_auth
from app.database import get_db
from app.workspaces.service import (
    create_workspace,
    delete_workspace,
    get_workspace,
    list_workspaces,
)

router = APIRouter(
    prefix="/api/workspaces", tags=["workspaces"], dependencies=[Depends(require_auth)]
)


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


@router.post("", response_model=WorkspaceOut, status_code=201)
def create(body: WorkspaceCreate, db: Session = Depends(get_db)) -> WorkspaceOut:
    ws = create_workspace(db, body.name)
    return WorkspaceOut.model_validate(ws)


@router.get("", response_model=list[WorkspaceOut])
def list_all(db: Session = Depends(get_db)) -> list[WorkspaceOut]:
    return [WorkspaceOut.model_validate(ws) for ws in list_workspaces(db)]


@router.get("/{ws_id}", response_model=WorkspaceOut)
def get_one(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> WorkspaceOut:
    ws = get_workspace(db, ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceOut.model_validate(ws)


@router.delete("/{ws_id}", status_code=204)
def delete(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not delete_workspace(db, ws_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
