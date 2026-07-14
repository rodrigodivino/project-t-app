from app.settings import settings


def verify_code(code: str) -> bool:
    return code == settings.access_code
