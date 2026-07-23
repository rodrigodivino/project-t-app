import uuid

from app.ai.read_and_extract import (
    ExtractionResult,
    Snippet,
    build_messages,
    build_prompt,
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
    prompt = build_prompt(SAMPLE_SCHEMA_TEXT, "<evidence-file/>", "<shoebox/>")
    assert "ev-1" in prompt


def test_build_prompt_empty_evidence():
    prompt = build_prompt(SAMPLE_SCHEMA_TEXT, "<evidence-file/>", "<shoebox/>")
    assert "<evidence-file/>" in prompt


def test_build_prompt_includes_existing_evidence():
    evidence_xml = (
        '<evidence-file>\n'
        '<evidence id="e1">Bairro X teve 100 postagens</evidence>\n'
        '<evidence id="e2">Conta Y postou 50 vezes</evidence>\n'
        '</evidence-file>'
    )
    prompt = build_prompt(SAMPLE_SCHEMA_TEXT, evidence_xml, "<shoebox/>")
    assert "Bairro X teve 100 postagens" in prompt
    assert "Conta Y postou 50 vezes" in prompt
    assert "evite duplicar" in prompt.lower()


def test_build_prompt_includes_shoebox_items():
    shoebox_xml = (
        '<shoebox>\n<item id="s1">\n  <query>SELECT COUNT(*) FROM t</query>\n'
        '  <explanation>Contagem total</explanation>\n  <row>\n    <count>42</count>\n'
        '  </row>\n</item>\n</shoebox>'
    )
    prompt = build_prompt(SAMPLE_SCHEMA_TEXT, "<evidence-file/>", shoebox_xml)
    assert "SELECT COUNT(*)" in prompt
    assert "Contagem total" in prompt
    assert "42" in prompt
    assert "s1" in prompt


def test_build_prompt_multiple_items():
    shoebox_xml = (
        '<shoebox>\n<item id="s1">\n  <query>Q1</query>\n  <explanation>E1</explanation>\n'
        '</item>\n<item id="s2">\n  <query>Q2</query>\n  <explanation>E2</explanation>\n'
        '</item>\n</shoebox>'
    )
    prompt = build_prompt(SAMPLE_SCHEMA_TEXT, "<evidence-file/>", shoebox_xml)
    assert "s1" in prompt
    assert "s2" in prompt
    assert "Q1" in prompt
    assert "Q2" in prompt


def test_build_messages_returns_two_messages():
    msgs = build_messages(SAMPLE_SCHEMA_TEXT, "<evidence-file/>", "<shoebox/>")
    assert len(msgs) == 2


def fake_llm(messages: list) -> ExtractionResult:
    return ExtractionResult(snippets=[
        Snippet(shoebox_id="PLACEHOLDER", content="Observação factual do item", rows=[0]),
    ])


def test_run_creates_evidence_items():
    session = FakeSession()
    ws_id = uuid.uuid4()
    item = FakeShoeboxItem()

    def llm_with_id(messages):
        return ExtractionResult(snippets=[
            Snippet(shoebox_id=str(item.id), content="Observação factual", rows=[0]),
        ])

    run(
        ws_id,
        llm_caller=llm_with_id,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: SAMPLE_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: [item],
        evidence_loader=lambda db, ws: [],
    )
    assert session.closed
    assert len(session.added) == 1
    added = session.added[0]
    assert added.workspace_id == ws_id
    assert added.content == "Observação factual"
    assert added.rows == [0]
    assert added.ai_authored is True


def test_run_skips_empty_shoebox():
    session = FakeSession()
    called = {"llm": False}

    def tracking_llm(messages):
        called["llm"] = True
        return ExtractionResult(snippets=[])

    run(
        uuid.uuid4(),
        llm_caller=tracking_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: SAMPLE_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: [],
        evidence_loader=lambda db, ws: [],
    )
    assert not called["llm"]
    assert session.closed


def test_run_handles_empty_extraction():
    session = FakeSession()

    def empty_llm(messages):
        return ExtractionResult(snippets=[])

    run(
        uuid.uuid4(),
        llm_caller=empty_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: SAMPLE_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: [FakeShoeboxItem()],
        evidence_loader=lambda db, ws: [],
    )
    assert len(session.added) == 0
    assert session.closed


def test_run_skips_unknown_shoebox_id():
    session = FakeSession()

    def bad_id_llm(messages):
        return ExtractionResult(snippets=[
            Snippet(shoebox_id="nonexistent", content="fact", rows=[0]),
        ])

    run(
        uuid.uuid4(),
        llm_caller=bad_id_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: SAMPLE_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: [FakeShoeboxItem()],
        evidence_loader=lambda db, ws: [],
    )
    assert len(session.added) == 0
    assert session.closed


def test_run_passes_evidence_titles_to_llm():
    session = FakeSession()
    received_messages = []

    def capturing_llm(messages):
        received_messages.extend(messages)
        return ExtractionResult(snippets=[])

    run(
        uuid.uuid4(),
        llm_caller=capturing_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: SAMPLE_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: [FakeShoeboxItem()],
        evidence_loader=lambda db, ws: [FakeEvidenceItem("Existing snippet")],
    )
    prompt_text = received_messages[1].content
    assert "Existing snippet" in prompt_text


def test_run_continues_on_snippet_failure():
    session = FakeSession()
    item = FakeShoeboxItem(result=[{"a": 1}, {"a": 2}])
    call_count = {"n": 0}
    original_add = session.add

    def failing_add(added_item):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated DB error")
        original_add(added_item)

    session.add = failing_add

    def multi_snippet_llm(messages):
        return ExtractionResult(snippets=[
            Snippet(shoebox_id=str(item.id), content="First", rows=[0]),
            Snippet(shoebox_id=str(item.id), content="Second", rows=[1]),
        ])

    run(
        uuid.uuid4(),
        llm_caller=multi_snippet_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: SAMPLE_SCHEMA_TREE,
        shoebox_loader=lambda db, ws: [item],
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
    from app.schematization.service import _normalize_data, serialize_xml
    tree = _normalize_data(schema_tree)
    evidence_map = {"ev-1": "fact one"}
    schema_context = serialize_xml(tree, evidence_map)
    prompt = build_prompt(schema_context, "<evidence-file/>", "<shoebox/>")
    assert 'elaborations="1"' in prompt
    assert 'questions="0"' in prompt
