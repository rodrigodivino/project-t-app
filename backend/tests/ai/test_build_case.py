import time
import uuid

from app.ai.build_case import (
    BuildCaseSuggestions,
    Suggestion,
    _all_tree_evidence_ids,
    build_messages,
    build_prompt,
    fire,
    run,
    serialize_schema_with_ids,
)


SAMPLE_SCHEMA_TREE = [
    {"type": "frame", "id": "f1", "title": "Hipótese", "description": "Desc",
     "children": [{"type": "evidence", "id": "ev-1", "rel": "elaborate"}]},
]
EMPTY_SCHEMA_TREE = []


class FakeEvidenceItem:
    def __init__(self, eid=None, content="evidência factual"):
        self.id = eid or uuid.uuid4()
        self.content = content


class FakeSchematization:
    def __init__(self, data):
        self.workspace_id = uuid.uuid4()
        self.data = data


class FakeSession:
    def __init__(self):
        self.closed = False
        self.committed = 0

    def get(self, model, pk):
        return None

    def commit(self):
        self.committed += 1

    def refresh(self, item):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True


FRAME_UUID = str(uuid.UUID("00000000-0000-0000-0000-ffffffffffff"))


def test_build_prompt_contains_evidence_and_schema():
    candidates = [("ev-99", "Conta A postou 50 vezes")]
    prompt = build_prompt("[f1] Frame: Hipótese", candidates)
    assert "f1" in prompt
    assert "Hipótese" in prompt
    assert "Conta A postou 50 vezes" in prompt
    assert "ev-99" in prompt


def test_build_prompt_asks_for_suggestions():
    prompt = build_prompt("schema", [("e1", "fact")])
    assert "evidence_id" in prompt
    assert "node_id" in prompt


def test_build_messages_returns_two_messages():
    msgs = build_messages("schema", [("e1", "evidence")])
    assert len(msgs) == 2


def test_serialize_schema_with_ids_includes_ids():
    evidence_map = {"ev-1": "Bairro X teve 100 postagens"}
    result = serialize_schema_with_ids(SAMPLE_SCHEMA_TREE, evidence_map)
    assert "[f1]" in result
    assert "[ev-1]" in result
    assert "Hipótese" in result
    assert "Bairro X teve 100 postagens" in result
    assert "Desc" in result


def test_serialize_schema_with_ids_shows_suggestions():
    tree = [
        {"type": "frame", "id": "f1", "title": "H", "description": "", "children": [
            {"type": "evidence", "id": "ev-1", "rel": "elaborate"},
            {"type": "evidence", "id": "ev-2", "rel": "elaborate", "suggestion": True},
        ]},
    ]
    evidence_map = {"ev-1": "fact one", "ev-2": "suggested fact"}
    result = serialize_schema_with_ids(tree, evidence_map)
    assert "fact one" in result
    assert "suggested fact" in result
    assert "[SUGESTÃO]" in result


def test_serialize_schema_with_ids_includes_balance():
    evidence_map = {"ev-1": "fact"}
    result = serialize_schema_with_ids(SAMPLE_SCHEMA_TREE, evidence_map)
    assert "Cobertura:" in result


def test_all_tree_evidence_ids_includes_suggestions():
    tree = [
        {"type": "evidence", "id": "e1"},
        {"type": "evidence", "id": "e2", "suggestion": True},
        {"type": "frame", "id": "f1", "title": "X", "children": [
            {"type": "evidence", "id": "e3", "rel": "elaborate"},
        ]},
    ]
    ids = _all_tree_evidence_ids(tree)
    assert set(ids) == {"e1", "e2", "e3"}



def fake_llm_match(
    schema_context: str, candidate_evidence: list[tuple[str, str]],
) -> BuildCaseSuggestions:
    return BuildCaseSuggestions(suggestions=[
        Suggestion(
            evidence_id=eid,
            node_id=FRAME_UUID,
            rel="elaborate",
        )
        for eid, _ in candidate_evidence
    ])


def fake_llm_none(
    schema_context: str, candidate_evidence: list[tuple[str, str]],
) -> BuildCaseSuggestions:
    return BuildCaseSuggestions(suggestions=[])


def test_run_creates_suggestion_nodes():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev = FakeEvidenceItem(content="Conta A postou 50 vezes")
    schema_data = [
        {"type": "frame", "id": FRAME_UUID, "title": "H", "description": "",
         "children": [{"type": "evidence", "id": "ev-1", "rel": "elaborate"}]},
    ]
    added_calls: list = []

    import app.schematization.service as svc
    original_add_evidence = svc.add_evidence

    def tracking_add_evidence(db, workspace_id, evidence_id, **kwargs):
        added_calls.append({"evidence_id": evidence_id, **kwargs})
        return FakeSchematization(schema_data)

    svc.add_evidence = tracking_add_evidence
    try:
        run(
            ws_id,
            llm_caller=fake_llm_match,
            session_factory=lambda: session,
            schema_loader=lambda db, ws: schema_data,
            evidence_loader=lambda db, ws: [ev],
            evidence_getter=lambda db, eid: ev if eid == ev.id else None,
        )
    finally:
        svc.add_evidence = original_add_evidence

    assert session.closed
    assert len(added_calls) == 1
    assert added_calls[0]["evidence_id"] == ev.id
    assert added_calls[0]["suggestion"] is True
    assert added_calls[0]["rel"] == "elaborate"
    assert added_calls[0]["parent_id"] == uuid.UUID(FRAME_UUID)



def test_run_skips_evidence_already_in_tree():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev = FakeEvidenceItem(eid=uuid.UUID("00000000-0000-0000-0000-000000000001"))
    schema_data = [
        {"type": "frame", "id": "f1", "title": "H", "description": "",
         "children": [
             {"type": "evidence", "id": "00000000-0000-0000-0000-000000000001",
              "rel": "elaborate"},
         ]},
    ]
    called = {"llm": False}

    def tracking_llm(schema_context, candidates):
        called["llm"] = True
        return BuildCaseSuggestions(suggestions=[])

    run(
        ws_id,
        llm_caller=tracking_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: schema_data,
        evidence_loader=lambda db, ws: [ev],
        evidence_getter=lambda db, eid: ev,
    )
    assert not called["llm"]
    assert session.closed


def test_run_skips_evidence_already_suggested():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev = FakeEvidenceItem(eid=uuid.UUID("00000000-0000-0000-0000-000000000002"))
    schema_data = [
        {"type": "frame", "id": "f1", "title": "H", "description": "",
         "children": [
             {"type": "evidence", "id": "00000000-0000-0000-0000-000000000002",
              "rel": "elaborate", "suggestion": True},
         ]},
    ]
    called = {"llm": False}

    def tracking_llm(schema_context, candidates):
        called["llm"] = True
        return BuildCaseSuggestions(suggestions=[])

    run(
        ws_id,
        llm_caller=tracking_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: schema_data,
        evidence_loader=lambda db, ws: [ev],
        evidence_getter=lambda db, eid: ev,
    )
    assert not called["llm"]
    assert session.closed


def test_run_handles_zero_suggestions():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev = FakeEvidenceItem()
    schema_data = [
        {"type": "frame", "id": "f1", "title": "H", "description": "",
         "children": [{"type": "evidence", "id": "ev-1", "rel": "elaborate"}]},
    ]

    import app.schematization.service as svc
    original = svc.add_evidence
    called = {"add": False}

    def tracking(db, workspace_id, evidence_id, **kwargs):
        called["add"] = True

    svc.add_evidence = tracking
    try:
        run(
            ws_id,
            llm_caller=fake_llm_none,
            session_factory=lambda: session,
            schema_loader=lambda db, ws: schema_data,
            evidence_loader=lambda db, ws: [ev],
            evidence_getter=lambda db, eid: ev,
        )
    finally:
        svc.add_evidence = original

    assert not called["add"]
    assert session.closed


def test_run_handles_invalid_node_id():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev = FakeEvidenceItem()
    schema_data = [
        {"type": "frame", "id": "f1", "title": "H", "description": "",
         "children": [{"type": "evidence", "id": "ev-1", "rel": "elaborate"}]},
    ]

    def bad_id_llm(schema_context, candidates):
        return BuildCaseSuggestions(suggestions=[
            Suggestion(
                evidence_id=candidates[0][0],
                node_id="not-a-uuid",
                rel="elaborate",
            ),
        ])

    run(
        ws_id,
        llm_caller=bad_id_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: schema_data,
        evidence_loader=lambda db, ws: [ev],
        evidence_getter=lambda db, eid: ev,
    )
    assert session.closed


def test_run_skips_empty_tree():
    session = FakeSession()
    called = {"llm": False}

    def tracking_llm(schema_context, candidates):
        called["llm"] = True
        return BuildCaseSuggestions(suggestions=[])

    run(
        uuid.uuid4(),
        llm_caller=tracking_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: EMPTY_SCHEMA_TREE,
        evidence_loader=lambda db, ws: [],
        evidence_getter=lambda db, eid: None,
    )
    assert not called["llm"]
    assert session.closed


def test_run_processes_specific_ids():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev_a = FakeEvidenceItem(content="A")
    ev_b = FakeEvidenceItem(content="B")
    schema_data = [
        {"type": "frame", "id": "f1", "title": "H", "description": "",
         "children": [{"type": "evidence", "id": "ev-1", "rel": "elaborate"}]},
    ]
    received = {}

    def capturing_llm(schema_context, candidates):
        received["candidates"] = candidates
        return BuildCaseSuggestions(suggestions=[])

    def getter(db, eid):
        if eid == ev_a.id:
            return ev_a
        if eid == ev_b.id:
            return ev_b
        return None

    run(
        ws_id,
        evidence_ids=[ev_a.id],
        llm_caller=capturing_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: schema_data,
        evidence_loader=lambda db, ws: [ev_a, ev_b],
        evidence_getter=getter,
    )
    assert len(received["candidates"]) == 1
    assert received["candidates"][0][1] == "A"
    assert session.closed


def test_fire_returns_immediately():
    start = time.monotonic()
    fire(uuid.uuid4())
    elapsed = time.monotonic() - start
    assert elapsed < 0.2
