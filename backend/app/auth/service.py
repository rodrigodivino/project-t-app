from app.settings import ACCESS_CODE


def verify_code(code: str) -> bool:
    return code == ACCESS_CODE
