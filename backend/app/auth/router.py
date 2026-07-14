from fastapi import APIRouter
from pydantic import BaseModel

from app.auth.service import verify_code

router = APIRouter(prefix="/api/auth", tags=["auth"])


class VerifyRequest(BaseModel):
    code: str


class VerifyResponse(BaseModel):
    valid: bool


@router.post("/verify", response_model=VerifyResponse)
def verify(request: VerifyRequest) -> VerifyResponse:
    return VerifyResponse(valid=verify_code(request.code))
