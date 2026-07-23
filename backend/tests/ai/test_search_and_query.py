import uuid
from datetime import datetime
from decimal import Decimal

from app.ai.search_and_query import (
    SearchQueries,
    SearchQuery,
    _clean_rows,
    build_prompt,
    run,
)


SAMPLE_SCHEMA_TEXT = "Frame: Hipótese\n  - [elabora] ev-1"
SAMPLE_SCHEMA_TREE = [
    {"type": "frame", "id": "f1", "title": "Hipótese", "description": "",
     "children": [{"type": "evidence", "id": "ev-1", "rel": "elaborate"}]},
]


def test_build_prompt_contains_schematization():
    prompt = build_prompt(SAMPLE_SCHEMA_TEXT, "<shoebox/>")
    assert "ev-1" in prompt
    assert "post_rede_social_himark" in prompt


def test_build_prompt_is_nonempty():
    prompt = build_prompt("", "<shoebox/>")
    assert len(prompt) > 0


def test_build_prompt_empty_shoebox():
    prompt = build_prompt(SAMPLE_SCHEMA_TEXT, "<shoebox/>")
    assert "<shoebox/>" in prompt


def test_build_prompt_includes_existing_items():
    shoebox_xml = (
        '<shoebox>\n<item id="abc">\n  <query>SELECT COUNT(*) FROM '
        'post_rede_social_himark</query>\n  <explanation>Contagem total'
        '</explanation>\n  <row>\n    <count>42</count>\n  </row>\n'
        '</item>\n</shoebox>'
    )
    prompt = build_prompt(SAMPLE_SCHEMA_TEXT, shoebox_xml)
    assert "SELECT COUNT(*)" in prompt
    assert "Contagem total" in prompt
    assert "42" in prompt


class FakeResult:
    def keys(self):
        return ["id", "message"]

    def fetchall(self):
        return [(1, "hello world")]


class FakeQuery:
    def __getattr__(self, name):
        def method(*args, **kwargs):
            return self
        return method

    def all(self):
        return []


class FakeSession:
    def __init__(self):
        self.added: list = []
        self.closed = False

    def execute(self, stmt):
        return FakeResult()

    def query(self, *args, **kwargs):
        return FakeQuery()

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


class FakeShoeboxItem:
    def __init__(self, sid=None, query="SELECT 1", explanation="test", result=None):
        self.id = sid or uuid.uuid4()
        self.query = query
        self.explanation = explanation
        self.result = result or [{"id": 1, "message": "hello"}]


def fake_llm(data: str, shoebox_xml: str) -> SearchQueries:
    return SearchQueries(queries=[
        SearchQuery(
            sql="SELECT id, message FROM post_rede_social_himark LIMIT 5",
            explanation="Buscar postagens recentes",
        ),
        SearchQuery(
            sql="SELECT account, COUNT(*) FROM post_rede_social_himark GROUP BY account",
            explanation="Contagem por conta",
        ),
    ])


def test_run_creates_shoebox_items():
    session = FakeSession()
    ws_id = uuid.uuid4()
    run(
        ws_id,
        SAMPLE_SCHEMA_TREE,
        llm_caller=fake_llm,
        session_factory=lambda: session,
        shoebox_loader=lambda db, ws: [],
    )
    assert session.closed
    assert len(session.added) == 2
    item = session.added[0]
    assert item.workspace_id == ws_id
    assert item.query == "SELECT id, message FROM post_rede_social_himark LIMIT 5"
    assert item.explanation == "Buscar postagens recentes"
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
        SAMPLE_SCHEMA_TREE,
        llm_caller=fake_llm,
        session_factory=lambda: session,
        shoebox_loader=lambda db, ws: [],
    )
    assert len(session.added) == 1
    assert session.closed


def test_run_handles_empty_queries():
    def empty_llm(data: str, shoebox_xml: str) -> SearchQueries:
        return SearchQueries(queries=[])

    session = FakeSession()
    ws_id = uuid.uuid4()
    run(
        ws_id,
        SAMPLE_SCHEMA_TREE,
        llm_caller=empty_llm,
        session_factory=lambda: session,
        shoebox_loader=lambda db, ws: [],
    )
    assert len(session.added) == 0
    assert session.closed


def test_run_passes_shoebox_xml_to_llm():
    received = {}

    def capturing_llm(data: str, shoebox_xml: str) -> SearchQueries:
        received["data"] = data
        received["shoebox_xml"] = shoebox_xml
        return SearchQueries(queries=[])

    item = FakeShoeboxItem(query="SELECT 1", explanation="test", result=[])
    session = FakeSession()
    ws_id = uuid.uuid4()
    run(
        ws_id,
        SAMPLE_SCHEMA_TREE,
        llm_caller=capturing_llm,
        session_factory=lambda: session,
        shoebox_loader=lambda db, ws: [item],
    )
    assert isinstance(received["data"], str)
    assert "Hipótese" in received["data"]
    assert isinstance(received["shoebox_xml"], str)
    assert str(item.id) in received["shoebox_xml"]


def test_clean_rows_serializes_datetime():
    rows = [
        {"hour": datetime(2020, 4, 7, 8, 0), "count": 605},
        {"id": uuid.UUID("12345678-1234-5678-1234-567812345678"), "val": "ok"},
        {"avg_length": Decimal("199.9"), "total": Decimal("42")},
    ]
    cleaned = _clean_rows(rows)
    assert cleaned[0]["hour"] == "2020-04-07T08:00:00"
    assert cleaned[0]["count"] == 605
    assert cleaned[1]["id"] == "12345678-1234-5678-1234-567812345678"
    assert cleaned[2]["avg_length"] == 199.9
    assert isinstance(cleaned[2]["avg_length"], float)
    assert cleaned[2]["total"] == 42.0


def test_prompt_includes_balance_annotation():
    schema_tree = [
        {"type": "frame", "id": "f1", "title": "Hipótese", "description": "",
         "children": [
             {"type": "evidence", "id": "ev-1", "rel": "elaborate"},
             {"type": "evidence", "id": "ev-2", "rel": "elaborate"},
         ]},
    ]
    from app.schematization.service import _normalize_data, serialize_xml
    from app.evidence import service as evidence_service
    tree = _normalize_data(schema_tree)
    evidence_map = {"ev-1": "fact one", "ev-2": "fact two"}
    schema_context = serialize_xml(tree, evidence_map)
    prompt = build_prompt(schema_context, "<shoebox/>")
    assert 'elaborations="2"' in prompt
    assert 'questions="0"' in prompt
