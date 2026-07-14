from fastapi import Header, HTTPException

from app.settings import ACCESS_CODE, PRODUCTION


def require_auth(authorization: str = Header(default="")) -> None:
    if not PRODUCTION:
        return
    if authorization != ACCESS_CODE:
        raise HTTPException(status_code=401, detail="Unauthorized")
