import time
import uuid
from datetime import datetime

from app.ai.search_and_query import (
    SearchQueries,
    SearchQuery,
    _clean_rows,
    build_prompt,
    fire,
    run,
)


SAMPLE_DATA = {"frames": [], "evidence": ["ev-1"], "relationships": []}


def test_build_prompt_contains_schematization():
    prompt = build_prompt(SAMPLE_DATA)
    assert "ev-1" in prompt
    assert "post_rede_social_himark" in prompt


def test_build_prompt_is_nonempty():
    prompt = build_prompt({"frames": [], "evidence": [], "relationships": []})
    assert len(prompt) > 0


class FakeResult:
    def keys(self):
        return ["id", "message"]

    def fetchall(self):
        return [(1, "hello world")]


class FakeSession:
    def __init__(self):
        self.added: list = []
        self.closed = False

    def execute(self, stmt):
        return FakeResult()

    def add(self, item):
        self.added.append(item)

    def commit(self):
        pass

    def refresh(self, item):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True


def fake_llm(data: dict) -> SearchQueries:
    return SearchQueries(queries=[
        SearchQuery(
            sql="SELECT id, message FROM post_rede_social_himark LIMIT 5",
            explanation="Get recent posts",
        ),
        SearchQuery(
            sql="SELECT account, COUNT(*) FROM post_rede_social_himark GROUP BY account",
            explanation="Count by account",
        ),
    ])


def test_run_creates_shoebox_items():
    session = FakeSession()
    ws_id = uuid.uuid4()
    run(
        ws_id,
        SAMPLE_DATA,
        llm_caller=fake_llm,
        session_factory=lambda: session,
    )
    assert session.closed
    assert len(session.added) == 2
    item = session.added[0]
    assert item.workspace_id == ws_id
    assert item.query == "SELECT id, message FROM post_rede_social_himark LIMIT 5"
    assert item.explanation == "Get recent posts"
    assert item.result == [{"id": 1, "message": "hello world"}]
    assert item.ai_authored is True


def test_run_continues_on_query_failure():
    class FailFirstSession(FakeSession):
        def __init__(self):
            super().__init__()
            self.call_count = 0

        def execute(self, stmt):
            self.call_count += 1
            if self.call_count == 1:
                raise RuntimeError("simulated SQL error")
            return FakeResult()

    session = FailFirstSession()
    ws_id = uuid.uuid4()
    run(
        ws_id,
        SAMPLE_DATA,
        llm_caller=fake_llm,
        session_factory=lambda: session,
    )
    assert len(session.added) == 1
    assert session.closed


def test_clean_rows_serializes_datetime():
    rows = [
        {"hour": datetime(2020, 4, 7, 8, 0), "count": 605},
        {"id": uuid.UUID("12345678-1234-5678-1234-567812345678"), "val": "ok"},
    ]
    cleaned = _clean_rows(rows)
    assert cleaned[0]["hour"] == "2020-04-07T08:00:00"
    assert cleaned[0]["count"] == 605
    assert cleaned[1]["id"] == "12345678-1234-5678-1234-567812345678"


def test_fire_returns_immediately():
    session = FakeSession()
    ws_id = uuid.uuid4()

    def slow_llm(data: dict) -> SearchQueries:
        time.sleep(0.5)
        return fake_llm(data)

    start = time.monotonic()
    fire(ws_id, SAMPLE_DATA)
    elapsed = time.monotonic() - start
    assert elapsed < 0.2
