import json
import logging
import threading
import uuid
from datetime import date, datetime
from typing import Callable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, SecretStr
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.settings import ANTHROPIC_API_KEY
from app.shoebox import service as shoebox_service
from app.sources import service as sources_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a data analyst. You have access to a PostgreSQL table called \
post_rede_social_himark with the following schema:

  id       INTEGER  PRIMARY KEY (auto-increment)
  time     TIMESTAMP  (ranges from 2020-04-06 00:00 to 2020-04-10 11:59)
  location TEXT
  account  TEXT
  message  TEXT

The possible location values are: Broadview, Chapparal, Cheddarford, \
Downtown, Easton, East Parton, <Location with-held due to contract>, \
Northwest, Oak Willow, Old Town, Palace Hills, Pepper Mill, Safe Town, \
Scenic Vista, Southton, Southwest, Terrapin Springs, UNKNOWN, Weston, \
West Parton, Wilson Forest.

The user is building a schematization to make sense of this data. \
A schematization contains frames (interpretive lenses), evidence \
references, and relationships between them.

Given the current schematization state, produce exactly 5 SQL SELECT \
queries that search the table for records relevant to the schematization. \
Each query should explore a different angle: temporal patterns, location \
clusters, account activity, keyword matches in messages, or cross-column \
correlations. Keep queries simple and fast. Always use the table name \
post_rede_social_himark. Do not use CTEs or subqueries unless necessary."""


class SearchQuery(BaseModel):
    sql: str
    explanation: str


class SearchQueries(BaseModel):
    queries: list[SearchQuery]


def build_prompt(schematization_data: dict) -> str:
    return (
        "Here is the current schematization state:\n\n"
        f"{json.dumps(schematization_data, indent=2)}\n\n"
        "Produce 5 SQL SELECT queries against post_rede_social_himark "
        "that would help the analyst explore data relevant to this "
        "schematization."
    )


def call_llm(schematization_data: dict) -> SearchQueries:
    llm = ChatAnthropic(
        model_name="claude-opus-4-8",
        api_key=SecretStr(ANTHROPIC_API_KEY),
        timeout=30,
        stop=None,
    )
    structured = llm.with_structured_output(SearchQueries)
    result = structured.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_prompt(schematization_data)),
    ])
    return result  # type: ignore[return-value]


def _make_serializable(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    return obj


def _clean_rows(rows: list[dict]) -> list[dict]:
    return [{k: _make_serializable(v) for k, v in row.items()} for row in rows]


def run(
    workspace_id: uuid.UUID,
    schematization_data: dict,
    llm_caller: Callable[[dict], SearchQueries] = call_llm,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    db: Session = session_factory()
    try:
        queries = llm_caller(schematization_data)
        for q in queries.queries:
            try:
                rows = sources_service.execute_query(db, q.sql)
                shoebox_service.add_item(
                    db, workspace_id, q.sql, q.explanation,
                    _clean_rows(rows), ai_authored=True,
                )
            except Exception:
                logger.exception("query failed: %s", q.sql)
                db.rollback()
    except Exception:
        logger.exception(
            "search_and_query failed for workspace %s", workspace_id
        )
    finally:
        db.close()


def fire(workspace_id: uuid.UUID, schematization_data: dict) -> None:
    thread = threading.Thread(
        target=run,
        args=(workspace_id, schematization_data),
        daemon=True,
    )
    thread.start()
