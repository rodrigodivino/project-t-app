import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependency import require_auth
from app.database import get_db
from app.story.service import get_or_create, update_content

router = APIRouter(
    prefix="/api/workspaces/{ws_id}/story",
    tags=["story"],
    dependencies=[Depends(require_auth)],
)


class StoryResponse(BaseModel):
    workspace_id: uuid.UUID
    content: str

    model_config = {"from_attributes": True}


class StoryUpdateRequest(BaseModel):
    content: str


@router.get("", response_model=StoryResponse)
def get(ws_id: uuid.UUID, db: Session = Depends(get_db)) -> StoryResponse:
    row = get_or_create(db, ws_id)
    return StoryResponse.model_validate(row)


@router.post("", response_model=StoryResponse)
def update(
    ws_id: uuid.UUID, body: StoryUpdateRequest, db: Session = Depends(get_db)
) -> StoryResponse:
    row = update_content(db, ws_id, body.content)
    return StoryResponse.model_validate(row)
