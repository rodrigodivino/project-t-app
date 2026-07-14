from fastapi import Header, HTTPException

from app.settings import ACCESS_CODE


def require_auth(authorization: str = Header()) -> None:
    if authorization != ACCESS_CODE:
        raise HTTPException(status_code=401, detail="Unauthorized")
