import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependency import require_auth
from app.database import get_db
from app.sources.service import execute_query

router = APIRouter(
    prefix="/api/workspaces/{ws_id}/sources",
    tags=["sources"],
    dependencies=[Depends(require_auth)],
)


class QueryRequest(BaseModel):
    query: str


@router.post("/query")
def query(
    ws_id: uuid.UUID, body: QueryRequest, db: Session = Depends(get_db)
) -> list[dict]:
    try:
        return execute_query(db, body.query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
