import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.schematization.models import Schematization

EMPTY_DATA: list = []


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
        if node.get("type") == "evidence" and not node.get("suggestion"):
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
    suggestion: bool = False,
    description: str = "",
) -> Schematization:
    row = get_or_create(db, workspace_id)
    eid = str(evidence_id)
    tree = _deep_copy_tree(row.data)

    _find_and_remove(tree, eid)

    node: dict = {"type": "evidence", "id": eid}
    if suggestion:
        node["suggestion"] = True
    if description:
        node["description"] = description
    if parent_id is not None:
        node["rel"] = rel

    if parent_id is not None:
        pid = str(parent_id)
        parent = _find_node(tree, pid)
        if parent is None:
            raise ValueError(f"Parent node {pid} not found")
        if parent.get("suggestion"):
            raise ValueError(f"Cannot add children to suggestion node {pid}")
        children = parent.setdefault("children", [])
        idx = index if index is not None else len(children)
        children.insert(idx, node)
    else:
        idx = index if index is not None else len(tree)
        tree.insert(idx, node)

    row.data = tree
    db.commit()
    db.refresh(row)
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


def approve_suggestion(
    db: Session,
    workspace_id: uuid.UUID,
    node_id: uuid.UUID,
) -> Schematization:
    row = get_or_create(db, workspace_id)
    nid = str(node_id)
    tree = _deep_copy_tree(row.data)
    node = _find_node(tree, nid)
    if node is None:
        raise ValueError(f"Node {nid} not found")
    if not node.get("suggestion"):
        raise ValueError(f"Node {nid} is not a suggestion")
    node.pop("suggestion", None)
    row.data = tree
    db.commit()
    db.refresh(row)
    return row


def update_node(
    db: Session,
    workspace_id: uuid.UUID,
    node_id: uuid.UUID,
    description: str | None = None,
) -> Schematization:
    row = get_or_create(db, workspace_id)
    nid = str(node_id)
    tree = _deep_copy_tree(row.data)
    node = _find_node(tree, nid)
    if node is None:
        raise ValueError(f"Node {nid} not found")
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

    moving = _find_node(tree, nid)
    if moving is not None and moving.get("suggestion"):
        raise ValueError("Cannot move a suggestion node")

    if parent_id is not None:
        pid = str(parent_id)
        target = _find_node(tree, pid)
        if target is None:
            raise ValueError(f"Parent node {pid} not found")
        if target.get("suggestion"):
            raise ValueError(f"Cannot add children to suggestion node {pid}")
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
    parent_list.pop(idx)

    row.data = tree
    db.commit()
    db.refresh(row)
    return row




def _is_empty_frame(node: dict) -> bool:
    return (
        node.get("type") == "frame"
        and not node.get("title")
        and not node.get("description")
        and not node.get("children")
    )


def strip_empty_frames(tree: list) -> list:
    return [n for n in tree if not _is_empty_frame(n)]


def strip_suggestions(tree: list) -> list:
    result = []
    for node in tree:
        if node.get("suggestion"):
            continue
        cleaned = dict(node)
        if "children" in cleaned:
            cleaned["children"] = strip_suggestions(cleaned["children"])
        result.append(cleaned)
    return result


def _count_children_by_rel(node: dict) -> dict[str, int]:
    counts = {"elaborate": 0, "question": 0, "cancel": 0}
    for child in node.get("children", []):
        if child.get("suggestion"):
            continue
        if child.get("type") == "evidence":
            rel = child.get("rel", "elaborate")
            if rel in counts:
                counts[rel] += 1
    return counts


def _xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _count_attrs(node: dict) -> str:
    counts = _count_children_by_rel(node)
    return (
        f'elaborations="{counts["elaborate"]}" '
        f'questions="{counts["question"]}" '
        f'cancellations="{counts["cancel"]}"'
    )


def serialize_xml(tree: list, evidence_map: dict[str, str]) -> str:
    lines: list[str] = ["<schematization>"]
    for node in tree:
        if node.get("suggestion"):
            continue
        if _is_empty_frame(node):
            continue
        if node.get("type") == "frame":
            _xml_frame(node, lines, evidence_map, indent=0)
        elif node.get("type") == "evidence":
            _xml_evidence_root(node, lines, evidence_map, indent=0)
    lines.append("</schematization>")
    return "\n".join(lines)


def _xml_frame(
    node: dict, lines: list[str], evidence_map: dict[str, str], indent: int,
) -> None:
    prefix = "  " * indent
    title = _xml_escape(node.get("title", ""))
    lines.append(f'{prefix}<frame title="{title}" {_count_attrs(node)}>')
    desc = node.get("description", "")
    if desc:
        lines.append(f"{prefix}  <description>{_xml_escape(desc)}</description>")
    for child in node.get("children", []):
        if child.get("suggestion"):
            continue
        if child.get("type") == "evidence":
            _xml_evidence(child, lines, evidence_map, indent + 1)
        elif child.get("type") == "frame":
            _xml_frame(child, lines, evidence_map, indent + 1)
    lines.append(f"{prefix}</frame>")


def _xml_evidence(
    node: dict, lines: list[str], evidence_map: dict[str, str], indent: int,
) -> None:
    prefix = "  " * indent
    rel = node.get("rel", "elaborate")
    content = evidence_map.get(node["id"], "?")
    lines.append(f'{prefix}<evidence rel="{rel}" {_count_attrs(node)}>')
    lines.append(f"{prefix}  <text>{_xml_escape(content)}</text>")
    desc = node.get("description", "")
    if desc:
        lines.append(f"{prefix}  <description>{_xml_escape(desc)}</description>")
    for child in node.get("children", []):
        if child.get("suggestion"):
            continue
        if child.get("type") == "evidence":
            _xml_evidence(child, lines, evidence_map, indent + 1)
        elif child.get("type") == "frame":
            _xml_frame(child, lines, evidence_map, indent + 1)
    lines.append(f"{prefix}</evidence>")


def _xml_evidence_root(
    node: dict, lines: list[str], evidence_map: dict[str, str], indent: int,
) -> None:
    prefix = "  " * indent
    content = evidence_map.get(node["id"], "?")
    lines.append(f"{prefix}<evidence>")
    lines.append(f"{prefix}  <text>{_xml_escape(content)}</text>")
    lines.append(f"{prefix}</evidence>")


ALL_RELS = {"elaborate", "question", "cancel"}


def _open_suggestion_slots(tree: list) -> dict[str, set[str]]:
    slots: dict[str, set[str]] = {}
    for node in tree:
        _collect_slots(node, slots)
    return slots


def _collect_slots(node: dict, slots: dict[str, set[str]]) -> None:
    if node.get("type") == "evidence" and node.get("suggestion"):
        return
    taken: set[str] = set()
    for child in node.get("children", []):
        if (
            child.get("type") == "evidence"
            and child.get("suggestion")
            and child.get("rel") in ALL_RELS
        ):
            taken.add(child["rel"])
        _collect_slots(child, slots)
    if node.get("type") in ("frame", "evidence"):
        open_rels = ALL_RELS - taken
        if open_rels:
            slots[node["id"]] = open_rels


def serialize_xml_suggestions(
    tree: list, evidence_map: dict[str, str],
    slots: dict[str, set[str]] | None = None,
) -> str:
    if slots is None:
        slots = {}
    lines: list[str] = ["<schematization>"]
    for node in tree:
        if _is_empty_frame(node):
            continue
        if node.get("type") == "frame":
            _xml_frame_sug(node, lines, evidence_map, slots, indent=0)
        elif node.get("type") == "evidence":
            if node.get("suggestion"):
                continue
            _xml_evidence_root_sug(node, lines, evidence_map, slots, indent=0)
    lines.append("</schematization>")
    return "\n".join(lines)


def _xml_slots(node_id: str, slots: dict[str, set[str]], lines: list[str], prefix: str) -> None:
    open_rels = slots.get(node_id)
    if not open_rels:
        return
    for rel in sorted(open_rels):
        lines.append(f'{prefix}<slot rel="{rel}"/>')


def _xml_frame_sug(
    node: dict, lines: list[str], evidence_map: dict[str, str],
    slots: dict[str, set[str]], indent: int,
) -> None:
    prefix = "  " * indent
    title = _xml_escape(node.get("title", ""))
    nid = node["id"]
    lines.append(f'{prefix}<frame id="{nid}" title="{title}" {_count_attrs(node)}>')
    desc = node.get("description", "")
    if desc:
        lines.append(f"{prefix}  <description>{_xml_escape(desc)}</description>")
    for child in node.get("children", []):
        if child.get("type") == "evidence":
            if child.get("suggestion"):
                _xml_evidence_suggestion(child, lines, evidence_map, indent + 1)
            else:
                _xml_evidence_sug(child, lines, evidence_map, slots, indent + 1)
        elif child.get("type") == "frame":
            _xml_frame_sug(child, lines, evidence_map, slots, indent + 1)
    _xml_slots(nid, slots, lines, prefix + "  ")
    lines.append(f"{prefix}</frame>")


def _xml_evidence_sug(
    node: dict, lines: list[str], evidence_map: dict[str, str],
    slots: dict[str, set[str]], indent: int,
) -> None:
    prefix = "  " * indent
    rel = node.get("rel", "elaborate")
    nid = node["id"]
    content = evidence_map.get(nid, "?")
    lines.append(f'{prefix}<evidence id="{nid}" rel="{rel}" {_count_attrs(node)}>')
    lines.append(f"{prefix}  <text>{_xml_escape(content)}</text>")
    desc = node.get("description", "")
    if desc:
        lines.append(f"{prefix}  <description>{_xml_escape(desc)}</description>")
    for child in node.get("children", []):
        if child.get("type") == "evidence":
            if child.get("suggestion"):
                _xml_evidence_suggestion(child, lines, evidence_map, indent + 1)
            else:
                _xml_evidence_sug(child, lines, evidence_map, slots, indent + 1)
        elif child.get("type") == "frame":
            _xml_frame_sug(child, lines, evidence_map, slots, indent + 1)
    _xml_slots(nid, slots, lines, prefix + "  ")
    lines.append(f"{prefix}</evidence>")


def _xml_evidence_root_sug(
    node: dict, lines: list[str], evidence_map: dict[str, str],
    slots: dict[str, set[str]], indent: int,
) -> None:
    prefix = "  " * indent
    nid = node["id"]
    content = evidence_map.get(nid, "?")
    lines.append(f'{prefix}<evidence id="{nid}" {_count_attrs(node)}>')
    lines.append(f"{prefix}  <text>{_xml_escape(content)}</text>")
    _xml_slots(nid, slots, lines, prefix + "  ")
    lines.append(f"{prefix}</evidence>")


def _xml_evidence_suggestion(
    node: dict, lines: list[str], evidence_map: dict[str, str], indent: int,
) -> None:
    prefix = "  " * indent
    rel = node.get("rel", "elaborate")
    content = evidence_map.get(node["id"], "?")
    lines.append(f'{prefix}<evidence suggestion="true" rel="{rel}">')
    lines.append(f"{prefix}  <text>{_xml_escape(content)}</text>")
    desc = node.get("description", "")
    if desc:
        lines.append(f"{prefix}  <description>{_xml_escape(desc)}</description>")
    lines.append(f"{prefix}</evidence>")
