from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.auth.router import router as auth_router
from app.database import engine
from app.sources.router import router as sources_router
from app.workspaces.router import router as workspaces_router

app = FastAPI()
app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(sources_router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/api/health")
def health() -> dict[str, str]:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
