import time
import uuid

from app.ai.read_and_extract import (
    ExtractionResult,
    Snippet,
    build_messages,
    build_prompt,
    fire,
    run,
)


SAMPLE_SCHEMA_TEXT = "Frame: Hipótese\n  - [elabora] ev-1"
SAMPLE_SCHEMA_TREE = [
    {"type": "frame", "id": "f1", "title": "Hipótese", "description": "",
     "children": [{"type": "evidence", "id": "ev-1", "rel": "elaborate"}]},
]
EMPTY_SCHEMA_TREE = []


class FakeEvidenceItem:
    def __init__(self, content="snippet text"):
        self.id = uuid.uuid4()
        self.content = content


class FakeShoeboxItem:
    def __init__(self, sid=None, query="SELECT 1", explanation="test", result=None):
        self.id = sid or uuid.uuid4()
        self.query = query
        self.explanation = explanation
        self.result = result or [{"id": 1, "message": "hello"}]


class FakeSession:
    def __init__(self):
        self.added: list = []
        self.closed = False

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


def test_build_prompt_contains_schematization():
    prompt = build_prompt(SAMPLE_SCHEMA_TEXT, [], {"query": "SELECT 1", "explanation": "x", "result": []})
    assert "ev-1" in prompt


def test_build_prompt_empty_evidence_message():
    prompt = build_prompt(SAMPLE_SCHEMA_TEXT, [], {"query": "SELECT 1", "explanation": "x", "result": []})
    assert "vazios" in prompt.lower()


def test_build_prompt_includes_existing_evidence():
    titles = ["Bairro X teve 100 postagens", "Conta Y postou 50 vezes"]
    prompt = build_prompt(
        SAMPLE_SCHEMA_TEXT, titles,
        {"query": "SELECT 1", "explanation": "x", "result": []},
    )
    assert "Bairro X teve 100 postagens" in prompt
    assert "Conta Y postou 50 vezes" in prompt
    assert "evite duplicar" in prompt.lower()


def test_build_prompt_includes_shoebox_item():
    item = {"query": "SELECT COUNT(*) FROM t", "explanation": "Contagem total", "result": [{"count": 42}]}
    prompt = build_prompt(SAMPLE_SCHEMA_TEXT, [], item)
    assert "SELECT COUNT(*)" in prompt
    assert "Contagem total" in prompt
    assert "42" in prompt


def test_build_messages_returns_two_messages():
    msgs = build_messages(SAMPLE_SCHEMA_TEXT, [], {"query": "Q", "explanation": "E", "result": []})
    assert len(msgs) == 2


def fake_llm_batch(inputs: list[list]) -> list[ExtractionResult]:
    return [
        ExtractionResult(snippets=[
            Snippet(content="Observação factual do item", rows=[0]),
        ])
        for _ in inputs
    ]


def test_run_creates_evidence_items():
    session = FakeSession()
    ws_id = uuid.uuid4()
    items = [FakeShoeboxItem(), FakeShoeboxItem()]
    run(
        ws_id,
        llm_caller=fake_llm_batch,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: SAMPLE_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: items,
        shoebox_getter=lambda db, sid: None,
        evidence_loader=lambda db, ws: [],
    )
    assert session.closed
    assert len(session.added) == 2
    item = session.added[0]
    assert item.workspace_id == ws_id
    assert item.content == "Observação factual do item"
    assert item.rows == [0]
    assert item.ai_authored is True


def test_run_skips_empty_schematization():
    session = FakeSession()
    called = {"llm": False}

    def tracking_llm(inputs):
        called["llm"] = True
        return []

    run(
        uuid.uuid4(),
        llm_caller=tracking_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: EMPTY_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: [],
        shoebox_getter=lambda db, sid: None,
        evidence_loader=lambda db, ws: [],
    )
    assert not called["llm"]
    assert session.closed


def test_run_handles_empty_extraction():
    session = FakeSession()

    def empty_llm(inputs):
        return [ExtractionResult(snippets=[]) for _ in inputs]

    run(
        uuid.uuid4(),
        llm_caller=empty_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: SAMPLE_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: [FakeShoeboxItem()],
        shoebox_getter=lambda db, sid: None,
        evidence_loader=lambda db, ws: [],
    )
    assert len(session.added) == 0
    assert session.closed


def test_run_processes_specific_ids():
    session = FakeSession()
    item_a = FakeShoeboxItem(sid=uuid.uuid4())
    item_b = FakeShoeboxItem(sid=uuid.uuid4())
    all_items = [item_a, item_b]

    def getter(db, sid):
        return next((i for i in all_items if i.id == sid), None)

    run(
        uuid.uuid4(),
        shoebox_ids=[item_a.id],
        llm_caller=fake_llm_batch,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: SAMPLE_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: all_items,
        shoebox_getter=getter,
        evidence_loader=lambda db, ws: [],
    )
    assert len(session.added) == 1
    assert session.closed


def test_run_passes_evidence_titles_to_llm():
    session = FakeSession()
    received_inputs = []

    def capturing_llm(inputs):
        received_inputs.extend(inputs)
        return [ExtractionResult(snippets=[]) for _ in inputs]

    run(
        uuid.uuid4(),
        llm_caller=capturing_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: SAMPLE_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: [FakeShoeboxItem()],
        shoebox_getter=lambda db, sid: None,
        evidence_loader=lambda db, ws: [FakeEvidenceItem("Existing snippet")],
    )
    prompt_text = received_inputs[0][1].content
    assert "Existing snippet" in prompt_text


def test_run_continues_on_snippet_failure():
    session = FakeSession()
    call_count = {"n": 0}

    original_add = session.add

    def failing_add(item):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated DB error")
        original_add(item)

    session.add = failing_add

    def multi_snippet_llm(inputs):
        return [
            ExtractionResult(snippets=[
                Snippet(content="First", rows=[0]),
                Snippet(content="Second", rows=[1]),
            ])
            for _ in inputs
        ]

    run(
        uuid.uuid4(),
        llm_caller=multi_snippet_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: SAMPLE_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: [FakeShoeboxItem(result=[{"a": 1}, {"a": 2}])],
        shoebox_getter=lambda db, sid: None,
        evidence_loader=lambda db, ws: [],
    )
    assert len(session.added) == 1
    assert session.closed


def test_prompt_includes_balance_annotation():
    schema_tree = [
        {"type": "frame", "id": "f1", "title": "Hipótese", "description": "",
         "children": [
             {"type": "evidence", "id": "ev-1", "rel": "elaborate"},
         ]},
    ]
    from app.schematization.service import _normalize_data, serialize_for_llm
    tree = _normalize_data(schema_tree)
    evidence_map = {"ev-1": "fact one"}
    schema_context = serialize_for_llm(tree, evidence_map)
    prompt = build_prompt(
        schema_context, [],
        {"query": "SELECT 1", "explanation": "x", "result": []},
    )
    assert "Cobertura:" in prompt
    assert "1× elabora" in prompt
    assert "0× questiona" in prompt


def test_fire_returns_immediately():
    start = time.monotonic()
    fire(uuid.uuid4())
    elapsed = time.monotonic() - start
    assert elapsed < 0.2
