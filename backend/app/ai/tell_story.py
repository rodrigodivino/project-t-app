import logging
import uuid
from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai import get_llm
from app.ai.read_and_extract import GLOSSARY
from app.database import SessionLocal
from app.evidence import service as evidence_service
from app.schematization import service as schematization_service
from app.story import service as story_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""\
{GLOSSARY}

Você opera no passo 4, "Tell a Story". Seu papel: articular a \
esquematização como um documento em linguagem natural, comunicando \
os frames e suas relações com evidências para um leitor externo.

Regras:
- A história deve representar fielmente o que a esquematização diz. \
Não adicione interpretações, inferências ou conclusões além do que \
os frames e evidências afirmam.
- Organize o texto de forma que cada frame corresponda a um \
parágrafo ou seção, descrevendo as evidências que o elaboram, \
questionam ou cancelam.
- Escreva em português do Brasil, em linguagem clara e direta.
- Se uma história anterior existir, atualize-a para refletir as \
mudanças na esquematização em vez de reescrevê-la do zero, \
preservando trechos que continuam válidos."""


class StoryOutput(BaseModel):
    content: str


def build_prompt(schema_context: str, current_story: str) -> str:
    parts = ["Esquematização atual:\n\n", schema_context, "\n\n"]
    if current_story.strip():
        parts.append("História atual:\n\n")
        parts.append(current_story)
        parts.append("\n\n")
        parts.append(
            "Atualize a história para refletir a esquematização acima. "
            "Preserve trechos que continuam válidos."
        )
    else:
        parts.append(
            "Produza uma história que articule a esquematização acima "
            "em linguagem natural."
        )
    return "".join(parts)


def build_messages(schema_context: str, current_story: str) -> list:
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_prompt(schema_context, current_story)),
    ]


def call_llm(schema_context: str, current_story: str) -> StoryOutput:
    structured = get_llm(timeout=60).with_structured_output(
        StoryOutput, method="json_schema",
    )
    messages = build_messages(schema_context, current_story)
    logger.warning(
        "tell_story LLM INPUT:\n%s",
        "\n---\n".join(m.content for m in messages),
    )
    result = structured.invoke(messages)
    logger.warning("tell_story LLM OUTPUT:\n%s", result)
    return result  # type: ignore[return-value]


def _default_schema_loader(db: Session, workspace_id: uuid.UUID) -> list:
    row = schematization_service.get_or_create(db, workspace_id)
    return row.data


def _default_evidence_loader(db: Session, workspace_id: uuid.UUID) -> list:
    return evidence_service.list_items(db, workspace_id)


def _default_story_loader(db: Session, workspace_id: uuid.UUID) -> str:
    row = story_service.get_or_create(db, workspace_id)
    return row.content


def run(
    workspace_id: uuid.UUID,
    llm_caller: Callable[[str, str], StoryOutput] = call_llm,
    session_factory: Callable[[], Session] = SessionLocal,
    schema_loader: Callable = _default_schema_loader,
    evidence_loader: Callable = _default_evidence_loader,
    story_loader: Callable = _default_story_loader,
) -> None:
    db: Session = session_factory()
    try:
        schema_data = schema_loader(db, workspace_id)
        from app.schematization.service import (
            _normalize_data,
            serialize_xml,
            strip_empty_frames,
            strip_suggestions,
        )

        tree = strip_suggestions(strip_empty_frames(_normalize_data(schema_data)))

        has_nodes = any(
            n.get("type") == "frame"
            or (n.get("type") == "evidence" and not n.get("suggestion"))
            for n in tree
        )
        if not has_nodes:
            logger.warning("tell_story: no frames/evidence in tree, skipping")
            return

        items = evidence_loader(db, workspace_id)
        evidence_map = {str(item.id): item.content for item in items}
        schema_context = serialize_xml(tree, evidence_map)

        current_story = story_loader(db, workspace_id)
        result = llm_caller(schema_context, current_story)

        story_service.update_content(db, workspace_id, result.content)
    except Exception:
        logger.exception("tell_story failed for workspace %s", workspace_id)
    finally:
        db.close()
