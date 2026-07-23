import uuid

from app.ai.tell_story import (
    StoryOutput,
    build_messages,
    build_prompt,
    run,
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


class FakeStory:
    def __init__(self, content=""):
        self.workspace_id = uuid.uuid4()
        self.content = content


class FakeSession:
    def __init__(self):
        self.closed = False
        self.committed = 0
        self.stored_content = None

    def get(self, model, pk):
        return None

    def add(self, item):
        pass

    def commit(self):
        self.committed += 1

    def refresh(self, item):
        pass

    def close(self):
        self.closed = True


def test_build_prompt_includes_schema():
    prompt = build_prompt("Frame: Hipótese\n  Desc", "")
    assert "Hipótese" in prompt
    assert "Produza uma história" in prompt


def test_build_prompt_includes_current_story():
    prompt = build_prompt("Frame: X", "história existente")
    assert "história existente" in prompt
    assert "Atualize a história" in prompt


def test_build_messages_has_system_and_human():
    messages = build_messages("schema", "")
    assert len(messages) == 2
    assert "Tell a Story" in messages[0].content


def test_run_noop_on_empty_schema():
    ws = uuid.uuid4()
    called = []

    def fake_llm(schema_ctx, story):
        called.append(True)
        return StoryOutput(content="text")

    run(
        ws,
        llm_caller=fake_llm,
        session_factory=FakeSession,
        schema_loader=lambda db, wid: [],
        evidence_loader=lambda db, wid: [],
        story_loader=lambda db, wid: "",
    )
    assert len(called) == 0


def test_run_calls_llm_and_saves():
    ws = uuid.uuid4()
    ev1 = FakeEvidenceItem(eid=uuid.UUID("00000000-0000-0000-0000-000000000001"))
    saved = []

    def fake_llm(schema_ctx, story):
        assert "Hipótese" in schema_ctx
        return StoryOutput(content="A história gerada.")

    from app.story import service as story_service
    original_update = story_service.update_content

    def track_update(db, wid, content):
        saved.append(content)
        return FakeStory(content)

    story_service.update_content = track_update
    try:
        run(
            ws,
            llm_caller=fake_llm,
            session_factory=FakeSession,
            schema_loader=lambda db, wid: list(SAMPLE_SCHEMA_TREE),
            evidence_loader=lambda db, wid: [ev1],
            story_loader=lambda db, wid: "",
        )
    finally:
        story_service.update_content = original_update

    assert len(saved) == 1
    assert saved[0] == "A história gerada."


def test_run_passes_current_story_to_llm():
    ws = uuid.uuid4()
    ev1 = FakeEvidenceItem(eid=uuid.UUID("00000000-0000-0000-0000-000000000001"))
    received_stories = []

    def fake_llm(schema_ctx, story):
        received_stories.append(story)
        return StoryOutput(content="updated")

    from app.story import service as story_service
    original_update = story_service.update_content
    story_service.update_content = lambda db, wid, content: FakeStory(content)
    try:
        run(
            ws,
            llm_caller=fake_llm,
            session_factory=FakeSession,
            schema_loader=lambda db, wid: list(SAMPLE_SCHEMA_TREE),
            evidence_loader=lambda db, wid: [ev1],
            story_loader=lambda db, wid: "previous story",
        )
    finally:
        story_service.update_content = original_update

    assert received_stories == ["previous story"]
