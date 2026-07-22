import logging
import threading
import uuid
from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai import get_llm
from app.database import SessionLocal
from app.evidence import service as evidence_service
from app.schematization import service as schematization_service
from app.ai.read_and_extract import GLOSSARY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""\
{GLOSSARY}

Você opera no passo "Build Case and Schematize". Seu papel: examinar \
um conjunto de evidências não posicionadas e decidir quais delas se \
relacionam com nós da esquematização.

Regras:
- Produza de 0 a 5 sugestões de posicionamento. Na dúvida, produza 1. \
O espaço para sugestões é limitado. Somente as relações mais \
relevantes e determinantes para a análise merecem lugar.
- Cada sugestão liga uma evidência a um nó existente (frame ou \
evidência) com uma relação (elaborate, question ou cancel).
- A evidência só pode ser colocada como filha de um frame ou de \
outra evidência. Nunca sugira colocação na raiz.
- Seja conservador. Só sugira posicionamento se a relação for clara \
e direta. Evidências sem relação clara ficam de fora.
- Prefira o nó mais específico. Se a evidência se relaciona com \
um frame e também com uma evidência filha desse frame, escolha \
a evidência filha.
- Mantenha o total de sugestões na esquematização em torno de 5. \
Contando as já existentes marcadas com [SUGESTÃO], produza somente \
o necessário para não ultrapassar esse limite.
- Evite acumular mais de 3 sugestões em um mesmo nó (contando as \
já existentes marcadas com [SUGESTÃO]).
- A relação deve refletir como a evidência se posiciona em relação \
ao nó pai: ela apoia (elaborate), questiona (question) ou \
invalida (cancel) o que o nó afirma?

Estratégia de equilíbrio:
- Examine a linha "Cobertura" de cada frame. Priorize sugestões que \
preencham lacunas na cobertura de relações. Um frame com 2 \
elaborações e 0 questionamentos precisa de evidências que o \
desafiem, não de mais apoio.
- Se uma relação cancel já existe em um nó, procure evidências que \
testem se essa invalidação se sustenta.
- Priorize frames no topo da árvore com menos filhos em vez de nós \
profundos que já possuem cobertura.
- O objetivo é amplitude pela árvore e equilíbrio entre relações, \
não profundidade em um único nó."""


class Suggestion(BaseModel):
    evidence_id: str
    node_id: str
    rel: str


class BuildCaseSuggestions(BaseModel):
    suggestions: list[Suggestion] = Field(default_factory=list)


REL_LABELS = {
    "elaborate": "+",
    "question": "?",
    "cancel": "✕",
}

REL_LABELS_PT = {
    "elaborate": "elabora",
    "question": "questiona",
    "cancel": "cancela",
}


def _all_tree_evidence_ids(tree: list) -> list[str]:
    ids: list[str] = []
    for node in tree:
        if node.get("type") == "evidence":
            ids.append(node["id"])
        for child in node.get("children", []):
            ids.extend(_all_tree_evidence_ids([child]))
    return ids



def _count_children_by_rel(node: dict) -> dict[str, int]:
    counts = {"elaborate": 0, "question": 0, "cancel": 0}
    for child in node.get("children", []):
        if child.get("type") == "evidence":
            rel = child.get("rel", "elaborate")
            if rel in counts:
                counts[rel] += 1
    return counts


def _format_balance(counts: dict[str, int]) -> str:
    total = sum(counts.values())
    if total == 0:
        return "Cobertura: nenhuma evidência"
    parts = []
    for rel, label in REL_LABELS_PT.items():
        parts.append(f"{counts.get(rel, 0)}× {label}")
    return f"Cobertura: {', '.join(parts)}"


def serialize_schema_with_ids(
    tree: list, evidence_map: dict[str, str],
) -> str:
    lines: list[str] = []
    for node in tree:
        if node.get("type") == "frame":
            _serialize_frame_with_id(node, lines, evidence_map, indent=0)
        elif node.get("type") == "evidence":
            if node.get("suggestion"):
                continue
            content = evidence_map.get(node["id"], "?")
            lines.append(f"[{node['id']}] {content}")
    return "\n".join(lines)


def _serialize_frame_with_id(
    node: dict, lines: list[str], evidence_map: dict[str, str], indent: int,
) -> None:
    prefix = "  " * indent
    lines.append(f"{prefix}[{node['id']}] Frame: {node.get('title', '')}")
    desc = node.get("description", "")
    if desc:
        lines.append(f"{prefix}  Descrição: {desc}")
    counts = _count_children_by_rel(node)
    lines.append(f"{prefix}  {_format_balance(counts)}")
    for child in node.get("children", []):
        if child.get("type") == "evidence":
            content = evidence_map.get(child["id"], "?")
            rel = child.get("rel", "elaborate")
            label = REL_LABELS.get(rel, rel)
            if child.get("suggestion"):
                lines.append(
                    f"{prefix}  [{child['id']}] [SUGESTÃO] [{label}] {content}"
                )
            else:
                lines.append(
                    f"{prefix}  [{child['id']}] [{label}] {content}"
                )
        elif child.get("type") == "frame":
            _serialize_frame_with_id(child, lines, evidence_map, indent + 1)


def build_prompt(
    schema_context: str, candidate_evidence: list[tuple[str, str]],
) -> str:
    parts = [
        "Estado atual da esquematização (IDs entre colchetes):\n\n",
        schema_context,
        "\n\n",
        "Evidências candidatas para posicionamento:\n\n",
    ]
    for i, (eid, content) in enumerate(candidate_evidence, 1):
        parts.append(f"  {i}. [{eid}] {content}\n")
    parts.append(
        "\nSugira de 0 a 5 posicionamentos. Para cada um, indique o "
        "evidence_id, o node_id do nó pai e a relação (elaborate, question "
        "ou cancel). Priorize equilíbrio entre relações e cobertura dos "
        "nós no topo da árvore."
    )
    return "".join(parts)


def build_messages(
    schema_context: str, candidate_evidence: list[tuple[str, str]],
) -> list:
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=build_prompt(schema_context, candidate_evidence),
        ),
    ]


def call_llm(
    schema_context: str, candidate_evidence: list[tuple[str, str]],
) -> BuildCaseSuggestions:
    structured = get_llm(timeout=60).with_structured_output(
        BuildCaseSuggestions, method="json_schema",
    )
    messages = build_messages(schema_context, candidate_evidence)
    result = structured.invoke(messages)
    return result  # type: ignore[return-value]


def _default_schema_loader(db: Session, workspace_id: uuid.UUID) -> list:
    row = schematization_service.get_or_create(db, workspace_id)
    return row.data


def _default_evidence_loader(db: Session, workspace_id: uuid.UUID) -> list:
    return evidence_service.list_items(db, workspace_id)


def _default_evidence_getter(db: Session, item_id: uuid.UUID):
    return evidence_service.get_item(db, item_id)


def run(
    workspace_id: uuid.UUID,
    evidence_ids: list[uuid.UUID] | None = None,
    llm_caller: Callable[
        [str, list[tuple[str, str]]], BuildCaseSuggestions
    ] = call_llm,
    session_factory: Callable[[], Session] = SessionLocal,
    schema_loader: Callable = _default_schema_loader,
    evidence_loader: Callable = _default_evidence_loader,
    evidence_getter: Callable = _default_evidence_getter,
) -> None:
    db: Session = session_factory()
    try:
        schema_data = schema_loader(db, workspace_id)
        from app.schematization.service import _normalize_data
        tree = _normalize_data(schema_data)

        has_nodes = any(
            n.get("type") == "frame" or (
                n.get("type") == "evidence" and not n.get("suggestion")
            )
            for n in tree
        )
        if not has_nodes:
            return

        placed_ids = set(_all_tree_evidence_ids(tree))

        if evidence_ids is not None:
            items = [evidence_getter(db, eid) for eid in evidence_ids]
            items = [i for i in items if i is not None]
        else:
            items = evidence_loader(db, workspace_id)

        candidates = [
            item for item in items if str(item.id) not in placed_ids
        ]
        if not candidates:
            return

        all_evidence = evidence_loader(db, workspace_id)
        evidence_map = {str(item.id): item.content for item in all_evidence}
        schema_context = serialize_schema_with_ids(tree, evidence_map)

        candidate_list = [
            (str(item.id), item.content) for item in candidates
        ]
        result = llm_caller(schema_context, candidate_list)

        candidate_id_set = {str(item.id) for item in candidates}

        for suggestion in result.suggestions:
            if suggestion.rel not in ("elaborate", "question", "cancel"):
                continue
            if suggestion.evidence_id not in candidate_id_set:
                continue
            try:
                schematization_service.add_evidence(
                    db,
                    workspace_id,
                    uuid.UUID(suggestion.evidence_id),
                    parent_id=uuid.UUID(suggestion.node_id),
                    rel=suggestion.rel,
                    suggestion=True,
                )
            except (ValueError, Exception):
                logger.exception(
                    "failed to add suggestion for evidence %s",
                    suggestion.evidence_id,
                )
                db.rollback()
    except Exception:
        logger.exception(
            "build_case failed for workspace %s", workspace_id
        )
    finally:
        db.close()


def fire(
    workspace_id: uuid.UUID,
    evidence_ids: list[uuid.UUID] | None = None,
) -> None:
    thread = threading.Thread(
        target=run,
        args=(workspace_id, evidence_ids),
        daemon=True,
    )
    thread.start()
