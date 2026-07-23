import uuid

from sqlalchemy.orm import Session

from app.shoebox.models import ShoeboxItem


def list_items(db: Session, workspace_id: uuid.UUID) -> list[ShoeboxItem]:
    return list(
        db.query(ShoeboxItem)
        .filter(ShoeboxItem.workspace_id == workspace_id)
        .order_by(ShoeboxItem.added_at.desc())
        .all()
    )


def get_item(db: Session, item_id: uuid.UUID) -> ShoeboxItem | None:
    return db.get(ShoeboxItem, item_id)


def add_item(
    db: Session,
    workspace_id: uuid.UUID,
    query: str,
    explanation: str,
    result: list[dict],
    ai_authored: bool = False,
    chart_spec: dict | None = None,
) -> ShoeboxItem:
    item = ShoeboxItem(
        workspace_id=workspace_id,
        query=query,
        explanation=explanation,
        result=result,
        chart_spec=chart_spec,
        ai_authored=ai_authored,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _xml_tag(name: str) -> str:
    safe = name.replace(" ", "_")
    if safe[0:1].isdigit():
        safe = f"_{safe}"
    return safe


def _xml_row(row: dict, prefix: str) -> list[str]:
    lines = [f"{prefix}<row>"]
    for col, val in row.items():
        tag = _xml_tag(col)
        lines.append(f"{prefix}  <{tag}>{_xml_escape(str(val))}</{tag}>")
    lines.append(f"{prefix}</row>")
    return lines


def _xml_item_lines(item: ShoeboxItem, indent: int) -> list[str]:
    prefix = "  " * indent
    lines = [f'{prefix}<item id="{item.id}">']
    lines.append(f"{prefix}  <query>{_xml_escape(item.query)}</query>")
    lines.append(f"{prefix}  <explanation>{_xml_escape(item.explanation)}</explanation>")
    for row in item.result:
        lines.extend(_xml_row(row, prefix + "  "))
    lines.append(f"{prefix}</item>")
    return lines


def serialize_xml(items: list[ShoeboxItem]) -> str:
    if not items:
        return "<shoebox/>"
    lines = ["<shoebox>"]
    for item in items:
        lines.extend(_xml_item_lines(item, indent=0))
    lines.append("</shoebox>")
    return "\n".join(lines)


def serialize_xml_item(item: ShoeboxItem) -> str:
    return "\n".join(_xml_item_lines(item, indent=0))


def remove_item(db: Session, item_id: uuid.UUID) -> bool:
    item = db.get(ShoeboxItem, item_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True
