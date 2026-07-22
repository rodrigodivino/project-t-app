import threading
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.ai import read_and_extract, search_and_query
from app.schematization.models import Schematization
from app import settings

EMPTY_DATA: list = []

_dirty: dict[uuid.UUID, Any] = {}
_dirty_lock = threading.Lock()
_ticker_started = False


def _normalize_data(data: Any) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "evidence" in data:
        return [
            {"type": "evidence", "id": eid}
            for eid in data.get("evidence", [])
        ]
    return []


def _all_evidence_ids(tree: list) -> list[str]:
    ids: list[str] = []
    for node in tree:
        if node.get("type") == "evidence":
            ids.append(node["id"])
        for child in node.get("children", []):
            ids.extend(_all_evidence_ids([child]))
    return ids


def _find_node(tree: list, node_id: str) -> dict | None:
    for node in tree:
        nid = node.get("id")
        if nid == node_id:
            return node
        found = _find_node(node.get("children", []), node_id)
        if found is not None:
            return found
    return None


def _find_and_remove(tree: list, node_id: str) -> dict | None:
    for i, node in enumerate(tree):
        if node.get("id") == node_id:
            return tree.pop(i)
        children = node.get("children", [])
        removed = _find_and_remove(children, node_id)
        if removed is not None:
            return removed
    return None


def _find_parent_and_index(tree: list, node_id: str) -> tuple[list, int] | None:
    for i, node in enumerate(tree):
        if node.get("id") == node_id:
            return tree, i
        children = node.get("children", [])
        found = _find_parent_and_index(children, node_id)
        if found is not None:
            return found
    return None


def _is_descendant(node: dict, ancestor_id: str) -> bool:
    if node.get("id") == ancestor_id:
        return True
    for child in node.get("children", []):
        if _is_descendant(child, ancestor_id):
            return True
    return False


def _deep_copy_tree(tree: list) -> list:
    import copy
    return copy.deepcopy(tree)


def get_or_create(db: Session, workspace_id: uuid.UUID) -> Schematization:
    row = db.get(Schematization, workspace_id)
    if row is not None:
        normalized = _normalize_data(row.data)
        if normalized != row.data:
            row.data = normalized
            db.commit()
            db.refresh(row)
        return row
    row = Schematization(workspace_id=workspace_id, data=list(EMPTY_DATA))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def add_evidence(
    db: Session,
    workspace_id: uuid.UUID,
    evidence_id: uuid.UUID,
    parent_id: uuid.UUID | None = None,
    index: int | None = None,
    rel: str = "elaborate",
) -> Schematization:
    row = get_or_create(db, workspace_id)
    eid = str(evidence_id)
    tree = _deep_copy_tree(row.data)

    _find_and_remove(tree, eid)

    node: dict = {"type": "evidence", "id": eid}
    if parent_id is not None:
        node["rel"] = rel

    if parent_id is not None:
        pid = str(parent_id)
        parent = _find_node(tree, pid)
        if parent is None:
            raise ValueError(f"Parent node {pid} not found")
        children = parent.setdefault("children", [])
        idx = index if index is not None else len(children)
        children.insert(idx, node)
    else:
        idx = index if index is not None else len(tree)
        tree.insert(idx, node)

    row.data = tree
    db.commit()
    db.refresh(row)
    _mark_dirty(workspace_id, row.data)
    return row


def remove_evidence(
    db: Session, workspace_id: uuid.UUID, evidence_id: uuid.UUID
) -> Schematization:
    row = get_or_create(db, workspace_id)
    tree = _deep_copy_tree(row.data)
    _find_and_remove(tree, str(evidence_id))
    row.data = tree
    db.commit()
    db.refresh(row)
    _mark_dirty(workspace_id, row.data)
    return row


def create_frame(
    db: Session,
    workspace_id: uuid.UUID,
    title: str,
    description: str = "",
) -> Schematization:
    row = get_or_create(db, workspace_id)
    tree = _deep_copy_tree(row.data)
    frame = {
        "type": "frame",
        "id": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "children": [],
    }
    tree.append(frame)
    row.data = tree
    db.commit()
    db.refresh(row)
    return row


def update_frame(
    db: Session,
    workspace_id: uuid.UUID,
    frame_id: uuid.UUID,
    title: str | None = None,
    description: str | None = None,
) -> Schematization:
    row = get_or_create(db, workspace_id)
    tree = _deep_copy_tree(row.data)
    node = _find_node(tree, str(frame_id))
    if node is None or node.get("type") != "frame":
        raise ValueError(f"Frame {frame_id} not found")
    if title is not None:
        node["title"] = title
    if description is not None:
        node["description"] = description
    row.data = tree
    db.commit()
    db.refresh(row)
    return row


def move_node(
    db: Session,
    workspace_id: uuid.UUID,
    node_id: uuid.UUID,
    parent_id: uuid.UUID | None = None,
    index: int | None = None,
    rel: str = "elaborate",
) -> Schematization:
    row = get_or_create(db, workspace_id)
    nid = str(node_id)
    tree = _deep_copy_tree(row.data)

    if parent_id is not None:
        pid = str(parent_id)
        target = _find_node(tree, pid)
        if target is None:
            raise ValueError(f"Parent node {pid} not found")
        moving = _find_node(tree, nid)
        if moving is not None and _is_descendant(moving, pid):
            raise ValueError("Cannot move a node into its own descendant")

    removed = _find_and_remove(tree, nid)
    if removed is None:
        raise ValueError(f"Node {nid} not found")

    if parent_id is not None:
        removed["rel"] = rel
        target = _find_node(tree, str(parent_id))
        children = target.setdefault("children", [])
        idx = index if index is not None else len(children)
        children.insert(idx, removed)
    else:
        removed.pop("rel", None)
        idx = index if index is not None else len(tree)
        tree.insert(idx, removed)

    row.data = tree
    db.commit()
    db.refresh(row)
    _mark_dirty(workspace_id, row.data)
    return row


def remove_node(
    db: Session, workspace_id: uuid.UUID, node_id: uuid.UUID
) -> Schematization:
    row = get_or_create(db, workspace_id)
    nid = str(node_id)
    tree = _deep_copy_tree(row.data)

    location = _find_parent_and_index(tree, nid)
    if location is None:
        raise ValueError(f"Node {nid} not found")
    parent_list, idx = location
    removed = parent_list.pop(idx)
    orphans = removed.get("children", [])
    for orphan in orphans:
        orphan.pop("rel", None)
    for i, orphan in enumerate(orphans):
        parent_list.insert(idx + i, orphan)

    row.data = tree
    db.commit()
    db.refresh(row)
    _mark_dirty(workspace_id, row.data)
    return row


def trigger_search(db: Session, workspace_id: uuid.UUID) -> None:
    if not settings.ANTHROPIC_API_KEY:
        return
    row = get_or_create(db, workspace_id)
    search_and_query.fire(workspace_id, row.data)


def trigger_extract(db: Session, workspace_id: uuid.UUID) -> None:
    if not settings.ANTHROPIC_API_KEY:
        return
    read_and_extract.fire(workspace_id)


def _mark_dirty(workspace_id: uuid.UUID, data: Any) -> None:
    if not settings.ANTHROPIC_API_KEY:
        return
    tree = _normalize_data(data)
    if not _all_evidence_ids(tree):
        return
    global _ticker_started
    with _dirty_lock:
        _dirty[workspace_id] = data
        if not _ticker_started:
            _ticker_started = True
            threading.Thread(target=_tick_loop, daemon=True).start()


def _tick_loop() -> None:
    while True:
        time.sleep(3)
        with _dirty_lock:
            batch = dict(_dirty)
            _dirty.clear()
        for wid, data in batch.items():
            search_and_query.fire(wid, data)
            read_and_extract.fire(wid)


def serialize_for_llm(tree: list, evidence_map: dict[str, str]) -> str:
    lines: list[str] = []
    loose: list[str] = []
    for node in tree:
        if node.get("type") == "frame":
            _serialize_frame(node, lines, evidence_map, indent=0)
        elif node.get("type") == "evidence":
            content = evidence_map.get(node["id"], "?")
            loose.append(content)
    if loose:
        lines.append("Evidências sem frame:")
        for content in loose:
            lines.append(f"- {content}")
    return "\n".join(lines)


def _serialize_frame(
    node: dict, lines: list[str], evidence_map: dict[str, str], indent: int,
) -> None:
    prefix = "  " * indent
    lines.append(f"{prefix}Frame: {node.get('title', '')}")
    desc = node.get("description", "")
    if desc:
        lines.append(f"{prefix}  Descrição: {desc}")
    for child in node.get("children", []):
        if child.get("type") == "evidence":
            content = evidence_map.get(child["id"], "?")
            rel = child.get("rel", "")
            rel_label = f"[{rel}] " if rel else ""
            lines.append(f"{prefix}  - {rel_label}{content}")
        elif child.get("type") == "frame":
            _serialize_frame(child, lines, evidence_map, indent + 1)
