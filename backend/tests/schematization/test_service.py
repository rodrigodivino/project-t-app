import uuid
from unittest.mock import MagicMock

from app.schematization.service import (
    _all_evidence_ids,
    _find_and_remove,
    _find_node,
    _normalize_data,
    add_evidence,
    create_frame,
    get_or_create,
    move_node,
    remove_evidence,
    remove_node,
    update_frame,
)


def test_normalize_old_format():
    old = {"frames": [], "evidence": ["e1", "e2"], "relationships": []}
    result = _normalize_data(old)
    assert result == [
        {"type": "evidence", "id": "e1"},
        {"type": "evidence", "id": "e2"},
    ]


def test_normalize_already_tree():
    tree = [{"type": "evidence", "id": "e1"}]
    assert _normalize_data(tree) is tree


def test_normalize_empty():
    assert _normalize_data({}) == []
    assert _normalize_data([]) == []


def test_all_evidence_ids_flat():
    tree = [
        {"type": "evidence", "id": "e1"},
        {"type": "frame", "id": "f1", "title": "X", "children": []},
        {"type": "evidence", "id": "e2"},
    ]
    assert _all_evidence_ids(tree) == ["e1", "e2"]


def test_all_evidence_ids_nested():
    tree = [
        {"type": "frame", "id": "f1", "title": "X", "children": [
            {"type": "evidence", "id": "e1", "rel": "elaborate"},
            {"type": "frame", "id": "f2", "title": "Y", "rel": "elaborate", "children": [
                {"type": "evidence", "id": "e2", "rel": "question"},
            ]},
        ]},
        {"type": "evidence", "id": "e3"},
    ]
    assert _all_evidence_ids(tree) == ["e1", "e2", "e3"]


def test_find_node():
    tree = [
        {"type": "frame", "id": "f1", "children": [
            {"type": "evidence", "id": "e1"},
        ]},
    ]
    assert _find_node(tree, "e1")["id"] == "e1"
    assert _find_node(tree, "f1")["id"] == "f1"
    assert _find_node(tree, "missing") is None


def test_find_and_remove():
    tree = [
        {"type": "evidence", "id": "e1"},
        {"type": "frame", "id": "f1", "children": [
            {"type": "evidence", "id": "e2"},
        ]},
    ]
    removed = _find_and_remove(tree, "e2")
    assert removed["id"] == "e2"
    assert tree[1]["children"] == []

    removed = _find_and_remove(tree, "e1")
    assert removed["id"] == "e1"
    assert len(tree) == 1


def test_get_or_create_existing():
    db = MagicMock()
    ws_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = [{"type": "evidence", "id": "e1"}]
    db.get.return_value = existing
    result = get_or_create(db, ws_id)
    assert result is existing
    db.add.assert_not_called()


def test_get_or_create_new():
    db = MagicMock()
    ws_id = uuid.uuid4()
    db.get.return_value = None
    result = get_or_create(db, ws_id)
    assert result.workspace_id == ws_id
    assert result.data == []
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_get_or_create_normalizes_old():
    db = MagicMock()
    ws_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = {"frames": [], "evidence": ["e1"], "relationships": []}
    db.get.return_value = existing
    get_or_create(db, ws_id)
    assert existing.data == [{"type": "evidence", "id": "e1"}]
    db.commit.assert_called_once()


def test_add_evidence_to_root():
    db = MagicMock()
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = []
    db.get.return_value = existing
    result = add_evidence(db, ws_id, ev_id)
    tree = result.data
    assert len(tree) == 1
    assert tree[0]["type"] == "evidence"
    assert tree[0]["id"] == str(ev_id)
    assert "rel" not in tree[0]


def test_add_evidence_to_root_at_index():
    db = MagicMock()
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = [{"type": "evidence", "id": "e0"}]
    db.get.return_value = existing
    result = add_evidence(db, ws_id, ev_id, index=0)
    tree = result.data
    assert tree[0]["id"] == str(ev_id)
    assert tree[1]["id"] == "e0"


def test_add_evidence_to_frame():
    db = MagicMock()
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    frame_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = [
        {"type": "frame", "id": str(frame_id), "title": "H", "children": []}
    ]
    db.get.return_value = existing
    result = add_evidence(db, ws_id, ev_id, parent_id=frame_id, rel="question")
    frame = result.data[0]
    assert len(frame["children"]) == 1
    assert frame["children"][0]["id"] == str(ev_id)
    assert frame["children"][0]["rel"] == "question"


def test_add_evidence_dedup_moves():
    db = MagicMock()
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    frame_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = [
        {"type": "evidence", "id": str(ev_id)},
        {"type": "frame", "id": str(frame_id), "title": "H", "children": []},
    ]
    db.get.return_value = existing
    result = add_evidence(db, ws_id, ev_id, parent_id=frame_id)
    assert len(result.data) == 1
    assert result.data[0]["children"][0]["id"] == str(ev_id)


def test_remove_evidence():
    db = MagicMock()
    ws_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = [{"type": "evidence", "id": str(ev_id)}]
    db.get.return_value = existing
    result = remove_evidence(db, ws_id, ev_id)
    assert result.data == []


def test_create_frame():
    db = MagicMock()
    ws_id = uuid.uuid4()
    existing = MagicMock()
    existing.data = []
    db.get.return_value = existing
    result = create_frame(db, ws_id, "Hipotese 1", "desc")
    assert len(result.data) == 1
    f = result.data[0]
    assert f["type"] == "frame"
    assert f["title"] == "Hipotese 1"
    assert f["description"] == "desc"
    assert f["children"] == []
    assert "id" in f


def test_update_frame():
    db = MagicMock()
    ws_id = uuid.uuid4()
    fid = str(uuid.uuid4())
    existing = MagicMock()
    existing.data = [
        {"type": "frame", "id": fid, "title": "Old", "description": "", "children": []}
    ]
    db.get.return_value = existing
    result = update_frame(db, ws_id, uuid.UUID(fid), title="New")
    assert result.data[0]["title"] == "New"
    assert result.data[0]["description"] == ""


def test_move_node_root_to_frame():
    db = MagicMock()
    ws_id = uuid.uuid4()
    eid = str(uuid.uuid4())
    fid = str(uuid.uuid4())
    existing = MagicMock()
    existing.data = [
        {"type": "evidence", "id": eid},
        {"type": "frame", "id": fid, "title": "H", "children": []},
    ]
    db.get.return_value = existing
    result = move_node(db, ws_id, uuid.UUID(eid), parent_id=uuid.UUID(fid), rel="cancel")
    assert len(result.data) == 1
    assert result.data[0]["children"][0]["id"] == eid
    assert result.data[0]["children"][0]["rel"] == "cancel"


def test_move_node_frame_to_root():
    db = MagicMock()
    ws_id = uuid.uuid4()
    eid = str(uuid.uuid4())
    fid = str(uuid.uuid4())
    existing = MagicMock()
    existing.data = [
        {"type": "frame", "id": fid, "title": "H", "children": [
            {"type": "evidence", "id": eid, "rel": "elaborate"},
        ]},
    ]
    db.get.return_value = existing
    result = move_node(db, ws_id, uuid.UUID(eid))
    assert len(result.data) == 2
    assert result.data[1]["id"] == eid
    assert "rel" not in result.data[1]


def test_move_node_prevents_cycle():
    db = MagicMock()
    ws_id = uuid.uuid4()
    fid = str(uuid.uuid4())
    child_fid = str(uuid.uuid4())
    existing = MagicMock()
    existing.data = [
        {"type": "frame", "id": fid, "title": "Parent", "children": [
            {"type": "frame", "id": child_fid, "title": "Child", "rel": "elaborate", "children": []},
        ]},
    ]
    db.get.return_value = existing
    try:
        move_node(db, ws_id, uuid.UUID(fid), parent_id=uuid.UUID(child_fid))
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_remove_node_splices_children():
    db = MagicMock()
    ws_id = uuid.uuid4()
    fid = str(uuid.uuid4())
    eid1 = str(uuid.uuid4())
    eid2 = str(uuid.uuid4())
    existing = MagicMock()
    existing.data = [
        {"type": "evidence", "id": "before"},
        {"type": "frame", "id": fid, "title": "H", "children": [
            {"type": "evidence", "id": eid1, "rel": "elaborate"},
            {"type": "evidence", "id": eid2, "rel": "question"},
        ]},
        {"type": "evidence", "id": "after"},
    ]
    db.get.return_value = existing
    result = remove_node(db, ws_id, uuid.UUID(fid))
    ids = [n["id"] for n in result.data]
    assert ids == ["before", eid1, eid2, "after"]
    assert "rel" not in result.data[1]
    assert "rel" not in result.data[2]
