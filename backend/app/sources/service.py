from sqlalchemy import text
from sqlalchemy.orm import Session


def execute_query(db: Session, sql: str) -> list[dict]:
    stripped = sql.strip().rstrip(";").strip()
    if not stripped.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")

    result = db.execute(text(sql))
    columns = list(result.keys())
    return [dict(zip(columns, row)) for row in result.fetchall()]
