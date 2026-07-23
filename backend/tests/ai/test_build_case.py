import uuid

from app.ai.build_case import (
    BuildCaseSuggestions,
    SYSTEM_PROMPT,
    Suggestion,
    _all_tree_evidence_ids,
    build_messages,
    build_prompt,
    run,
)
from app.schematization.service import (
    _open_suggestion_slots,
    serialize_xml_suggestions,
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
    candidate_xml = '<evidence-file>\n<evidence id="ev-99">Conta A postou 50 vezes</evidence>\n</evidence-file>'
    prompt = build_prompt("[f1] Frame: Hipótese", candidate_xml)
    assert "f1" in prompt
    assert "Hipótese" in prompt
    assert "Conta A postou 50 vezes" in prompt
    assert "ev-99" in prompt


def test_build_prompt_asks_for_suggestions():
    prompt = build_prompt("schema", "<evidence-file/>")
    assert "evidence_id" in prompt
    assert "node_id" in prompt


def test_system_prompt_requests_bare_uuids():
    assert "sem colchetes" in SYSTEM_PROMPT


def test_build_messages_returns_two_messages():
    msgs = build_messages("schema", "<evidence-file/>")
    assert len(msgs) == 2


def test_serialize_xml_suggestions_includes_ids():
    evidence_map = {"ev-1": "Bairro X teve 100 postagens"}
    result = serialize_xml_suggestions(SAMPLE_SCHEMA_TREE, evidence_map)
    assert 'id="f1"' in result
    assert 'id="ev-1"' in result
    assert "Hipótese" in result
    assert "Bairro X teve 100 postagens" in result
    assert "Desc" in result


def test_serialize_xml_suggestions_shows_suggestions():
    tree = [
        {"type": "frame", "id": "f1", "title": "H", "description": "", "children": [
            {"type": "evidence", "id": "ev-1", "rel": "elaborate"},
            {"type": "evidence", "id": "ev-2", "rel": "elaborate", "suggestion": True},
        ]},
    ]
    evidence_map = {"ev-1": "fact one", "ev-2": "suggested fact"}
    result = serialize_xml_suggestions(tree, evidence_map)
    assert "fact one" in result
    assert "suggested fact" in result
    assert 'suggestion="true"' in result
    assert 'id="ev-2"' not in result


def test_serialize_xml_suggestions_includes_counts():
    evidence_map = {"ev-1": "fact"}
    result = serialize_xml_suggestions(SAMPLE_SCHEMA_TREE, evidence_map)
    assert 'elaborations="1"' in result


def test_serialize_xml_suggestions_shows_open_slots():
    tree = [
        {"type": "frame", "id": "f1", "title": "H", "description": "", "children": [
            {"type": "evidence", "id": "ev-1", "rel": "elaborate"},
            {"type": "evidence", "id": "ev-2", "rel": "elaborate", "suggestion": True},
        ]},
    ]
    evidence_map = {"ev-1": "fact one", "ev-2": "suggested fact"}
    slots = _open_suggestion_slots(tree)
    result = serialize_xml_suggestions(tree, evidence_map, slots)
    assert '<slot rel=' in result
    assert 'rel="question"' in result
    assert 'rel="cancel"' in result


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


def test_open_slots_all_open_on_empty_children():
    tree = [
        {"type": "frame", "id": "f1", "title": "H", "children": []},
    ]
    slots = _open_suggestion_slots(tree)
    assert slots["f1"] == {"elaborate", "question", "cancel"}


def test_open_slots_blocked_by_existing_suggestion():
    tree = [
        {"type": "frame", "id": "f1", "title": "H", "children": [
            {"type": "evidence", "id": "ev-1", "rel": "elaborate", "suggestion": True},
        ]},
    ]
    slots = _open_suggestion_slots(tree)
    assert "elaborate" not in slots["f1"]
    assert "question" in slots["f1"]
    assert "cancel" in slots["f1"]


def test_open_slots_confirmed_card_does_not_block():
    tree = [
        {"type": "frame", "id": "f1", "title": "H", "children": [
            {"type": "evidence", "id": "ev-1", "rel": "elaborate"},
        ]},
    ]
    slots = _open_suggestion_slots(tree)
    assert "elaborate" in slots["f1"]


def test_open_slots_excludes_suggestion_nodes():
    tree = [
        {"type": "frame", "id": "f1", "title": "H", "children": [
            {"type": "evidence", "id": "ev-1", "rel": "elaborate", "suggestion": True},
        ]},
    ]
    slots = _open_suggestion_slots(tree)
    assert "ev-1" not in slots


def test_open_slots_includes_confirmed_evidence_nodes():
    tree = [
        {"type": "frame", "id": "f1", "title": "H", "children": [
            {"type": "evidence", "id": "ev-1", "rel": "elaborate", "children": []},
        ]},
    ]
    slots = _open_suggestion_slots(tree)
    assert "ev-1" in slots
    assert slots["ev-1"] == {"elaborate", "question", "cancel"}


def test_open_slots_empty_when_all_taken():
    tree = [
        {"type": "frame", "id": "f1", "title": "H", "children": [
            {"type": "evidence", "id": "s1", "rel": "elaborate", "suggestion": True},
            {"type": "evidence", "id": "s2", "rel": "question", "suggestion": True},
            {"type": "evidence", "id": "s3", "rel": "cancel", "suggestion": True},
        ]},
    ]
    slots = _open_suggestion_slots(tree)
    assert "f1" not in slots


def fake_llm_none(
    schema_context: str, candidate_xml: str,
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

    def llm_match(schema_context, candidate_xml):
        return BuildCaseSuggestions(suggestions=[
            Suggestion(evidence_id=str(ev.id), node_id=FRAME_UUID, rel="elaborate"),
        ])

    svc.add_evidence = tracking_add_evidence
    try:
        run(
            ws_id,
            llm_caller=llm_match,
            session_factory=lambda: session,
            schema_loader=lambda db, ws: schema_data,
            evidence_loader=lambda db, ws: [ev],
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

    def bad_id_llm(schema_context, candidate_xml):
        return BuildCaseSuggestions(suggestions=[
            Suggestion(
                evidence_id=str(ev.id),
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
    )
    assert session.closed


def test_run_skips_empty_tree():
    session = FakeSession()
    called = {"llm": False}

    def tracking_llm(schema_context, candidate_xml):
        called["llm"] = True
        return BuildCaseSuggestions(suggestions=[])

    run(
        uuid.uuid4(),
        llm_caller=tracking_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: EMPTY_SCHEMA_TREE,
        evidence_loader=lambda db, ws: [],
    )
    assert not called["llm"]
    assert session.closed


def test_run_processes_all_unplaced_evidence():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev_a = FakeEvidenceItem(content="A")
    ev_b = FakeEvidenceItem(content="B")
    schema_data = [
        {"type": "frame", "id": "f1", "title": "H", "description": "",
         "children": [{"type": "evidence", "id": "ev-1", "rel": "elaborate"}]},
    ]
    received = {}

    def capturing_llm(schema_context, candidate_xml):
        received["candidate_xml"] = candidate_xml
        return BuildCaseSuggestions(suggestions=[])

    run(
        ws_id,
        llm_caller=capturing_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: schema_data,
        evidence_loader=lambda db, ws: [ev_a, ev_b],
    )
    assert str(ev_a.id) in received["candidate_xml"]
    assert str(ev_b.id) in received["candidate_xml"]
    assert session.closed


def test_run_rejects_duplicate_node_rel_in_response():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev_a = FakeEvidenceItem(content="A")
    ev_b = FakeEvidenceItem(content="B")
    schema_data = [
        {"type": "frame", "id": FRAME_UUID, "title": "H", "description": "",
         "children": []},
    ]
    added_calls: list = []

    import app.schematization.service as svc
    original = svc.add_evidence

    def tracking(db, workspace_id, evidence_id, **kwargs):
        added_calls.append({"evidence_id": evidence_id, **kwargs})
        return FakeSchematization(schema_data)

    def llm_two_elaborate(schema_context, candidate_xml):
        return BuildCaseSuggestions(suggestions=[
            Suggestion(evidence_id=str(ev_a.id), node_id=FRAME_UUID, rel="elaborate"),
            Suggestion(evidence_id=str(ev_b.id), node_id=FRAME_UUID, rel="elaborate"),
        ])

    svc.add_evidence = tracking
    try:
        run(
            ws_id,
            llm_caller=llm_two_elaborate,
            session_factory=lambda: session,
            schema_loader=lambda db, ws: schema_data,
            evidence_loader=lambda db, ws: [ev_a, ev_b],
        )
    finally:
        svc.add_evidence = original

    assert len(added_calls) == 1


def test_run_skips_when_no_open_slots():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev = FakeEvidenceItem()
    schema_data = [
        {"type": "frame", "id": "f1", "title": "H", "description": "",
         "children": [
             {"type": "evidence", "id": "s1", "rel": "elaborate", "suggestion": True},
             {"type": "evidence", "id": "s2", "rel": "question", "suggestion": True},
             {"type": "evidence", "id": "s3", "rel": "cancel", "suggestion": True},
         ]},
    ]
    called = {"llm": False}

    def tracking_llm(schema_context, candidate_xml):
        called["llm"] = True
        return BuildCaseSuggestions(suggestions=[])

    run(
        ws_id,
        llm_caller=tracking_llm,
        session_factory=lambda: session,
        schema_loader=lambda db, ws: schema_data,
        evidence_loader=lambda db, ws: [ev],
    )
    assert not called["llm"]
    assert session.closed


def test_run_rejects_suggestion_targeting_closed_slot():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev = FakeEvidenceItem()
    schema_data = [
        {"type": "frame", "id": FRAME_UUID, "title": "H", "description": "",
         "children": [
             {"type": "evidence", "id": "s1", "rel": "elaborate", "suggestion": True},
         ]},
    ]
    added_calls: list = []

    import app.schematization.service as svc
    original = svc.add_evidence

    def tracking(db, workspace_id, evidence_id, **kwargs):
        added_calls.append({"evidence_id": evidence_id, **kwargs})
        return FakeSchematization(schema_data)

    def llm_elaborate(schema_context, candidate_xml):
        return BuildCaseSuggestions(suggestions=[
            Suggestion(evidence_id=str(ev.id), node_id=FRAME_UUID, rel="elaborate"),
        ])

    svc.add_evidence = tracking
    try:
        run(
            ws_id,
            llm_caller=llm_elaborate,
            session_factory=lambda: session,
            schema_loader=lambda db, ws: schema_data,
            evidence_loader=lambda db, ws: [ev],
        )
    finally:
        svc.add_evidence = original

    assert len(added_calls) == 0


def test_run_allows_different_rel_on_same_node():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev_a = FakeEvidenceItem(content="A")
    ev_b = FakeEvidenceItem(content="B")
    schema_data = [
        {"type": "frame", "id": FRAME_UUID, "title": "H", "description": "",
         "children": []},
    ]
    added_calls: list = []

    import app.schematization.service as svc
    original = svc.add_evidence

    def tracking(db, workspace_id, evidence_id, **kwargs):
        added_calls.append({"evidence_id": evidence_id, **kwargs})
        return FakeSchematization(schema_data)

    def llm_two_rels(schema_context, candidate_xml):
        return BuildCaseSuggestions(suggestions=[
            Suggestion(evidence_id=str(ev_a.id), node_id=FRAME_UUID, rel="elaborate"),
            Suggestion(evidence_id=str(ev_b.id), node_id=FRAME_UUID, rel="question"),
        ])

    svc.add_evidence = tracking
    try:
        run(
            ws_id,
            llm_caller=llm_two_rels,
            session_factory=lambda: session,
            schema_loader=lambda db, ws: schema_data,
            evidence_loader=lambda db, ws: [ev_a, ev_b],
        )
    finally:
        svc.add_evidence = original

    assert len(added_calls) == 2
    assert added_calls[0]["rel"] == "elaborate"
    assert added_calls[1]["rel"] == "question"


def test_suggestion_model_accepts_description():
    s = Suggestion(
        evidence_id="e1", node_id="n1", rel="elaborate",
        description="Esta evidência apoia a hipótese.",
    )
    assert s.description == "Esta evidência apoia a hipótese."


def test_suggestion_model_defaults_empty_description():
    s = Suggestion(evidence_id="e1", node_id="n1", rel="elaborate")
    assert s.description == ""


def test_run_passes_description_to_add_evidence():
    session = FakeSession()
    ws_id = uuid.uuid4()
    ev = FakeEvidenceItem(content="Conta A postou 50 vezes")
    schema_data = [
        {"type": "frame", "id": FRAME_UUID, "title": "H", "description": "",
         "children": [{"type": "evidence", "id": "ev-1", "rel": "elaborate"}]},
    ]
    added_calls: list = []

    import app.schematization.service as svc
    original = svc.add_evidence

    def tracking(db, workspace_id, evidence_id, **kwargs):
        added_calls.append({"evidence_id": evidence_id, **kwargs})
        return FakeSchematization(schema_data)

    def llm_with_desc(schema_context, candidate_xml):
        return BuildCaseSuggestions(suggestions=[
            Suggestion(
                evidence_id=str(ev.id),
                node_id=FRAME_UUID,
                rel="elaborate",
                description="Apoia a hipótese com dados concretos.",
            ),
        ])

    svc.add_evidence = tracking
    try:
        run(
            ws_id,
            llm_caller=llm_with_desc,
            session_factory=lambda: session,
            schema_loader=lambda db, ws: schema_data,
            evidence_loader=lambda db, ws: [ev],
        )
    finally:
        svc.add_evidence = original

    assert len(added_calls) == 1
    assert added_calls[0]["description"] == "Apoia a hipótese com dados concretos."


def test_serialize_xml_suggestions_includes_evidence_description():
    tree = [
        {"type": "frame", "id": "f1", "title": "H", "description": "", "children": [
            {"type": "evidence", "id": "ev-1", "rel": "elaborate",
             "description": "Apoia com dados concretos"},
        ]},
    ]
    evidence_map = {"ev-1": "fact one"}
    result = serialize_xml_suggestions(tree, evidence_map)
    assert "<description>Apoia com dados concretos</description>" in result


def test_serialize_xml_suggestions_recurses_evidence_children():
    tree = [
        {"type": "frame", "id": "f1", "title": "H", "description": "", "children": [
            {"type": "evidence", "id": "ev-1", "rel": "elaborate", "children": [
                {"type": "evidence", "id": "ev-2", "rel": "cancel",
                 "description": "contradicts parent"},
            ]},
        ]},
    ]
    evidence_map = {"ev-1": "parent fact", "ev-2": "child fact"}
    slots = _open_suggestion_slots(tree)
    result = serialize_xml_suggestions(tree, evidence_map, slots)
    assert "parent fact" in result
    assert "child fact" in result
    assert 'id="ev-2"' in result
    assert "contradicts parent" in result


def test_suggestion_strips_whitespace():
    s = Suggestion(
        evidence_id=" b47b0f36-4e23-496c-a972-c206d8f36cfe",
        node_id=" 51c6df90-25a5-471a-b496-7f2b045183f2",
        rel=" question",
        description=" Leading space description. ",
    )
    assert s.evidence_id == "b47b0f36-4e23-496c-a972-c206d8f36cfe"
    assert s.node_id == "51c6df90-25a5-471a-b496-7f2b045183f2"
    assert s.rel == "question"
    assert s.description == "Leading space description."


def test_system_prompt_requests_description():
    assert "description" in SYSTEM_PROMPT
