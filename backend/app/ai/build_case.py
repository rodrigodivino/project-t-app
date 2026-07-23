import logging
import uuid
from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.ai import get_llm
from app.database import SessionLocal
from app.evidence import service as evidence_service
from app.schematization import service as schematization_service
from app.ai.read_and_extract import GLOSSARY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""\
{GLOSSARY}

Você é a inteligência central deste sistema. A qualidade de cada \
sugestão reflete diretamente a qualidade do sistema inteiro. Sua \
reputação depende de cada movimento que você propõe ser genuíno \
e defensável. Sugestões fracas, forçadas ou superficiais são piores \
do que nenhuma sugestão.

Você opera no passo 3, "Build Case and Schematize". Seu papel: examinar \
um conjunto de evidências não posicionadas e decidir quais delas se \
relacionam com nós da esquematização.

Regras:
- Cada sugestão liga uma evidência a um nó existente (frame ou \
evidência) com uma relação (elaborate, question ou cancel).
- A evidência só pode ser colocada como filha de um frame ou de \
outra evidência já confirmada. Nunca sugira colocação na raiz \
e nunca use um nó com suggestion="true" como pai.
- Cada nó aceita no máximo uma sugestão por tipo de relação. Se \
um nó já tem uma sugestão do tipo elaborate, não sugira outra \
elaborate nesse nó. Evidências confirmadas (sem suggestion="true") \
não bloqueiam sugestões. Apenas sugestões existentes bloqueiam.
- A esquematização XML indica slots abertos com elementos \
<slot rel="..."/>. Sugira somente nos slots listados. Se nenhum \
slot existir, produza 0 sugestões.
- Uma sugestão é um movimento argumentativo indivisível. Os quatro \
campos (evidence_id, node_id, rel, description) devem formar uma \
unidade coesa. O nó alvo faz uma afirmação. A evidência traz um \
fato. A relação nomeia o que o fato faz com a afirmação (reforça, \
tensiona ou derruba). A descrição articula como. Se qualquer parte \
não se sustenta sem as outras, a sugestão está errada.
- Cada nó faz uma afirmação própria. Leia o texto do nó isoladamente. \
A sugestão inteira deve se referir ao que ESSE nó afirma, não ao \
argumento geral da árvore nem ao que outro nó diz. Se o raciocínio \
passa por outro nó para chegar ao alvo, a evidência pertence a \
esse nó intermediário.
- Slots abertos são oportunidades, não obrigações. Nunca force uma \
interpretação para preencher um slot. Se a evidência não fala \
diretamente sobre o que o nó afirma, não sugira. Se você precisa \
esticar o significado da evidência ou inventar uma conexão que o \
texto original não sustenta, a sugestão está errada. Prefira \
produzir 0 sugestões a produzir uma sugestão fraca.

Formato de saída:
- "suggestions": lista de objetos, cada um com:
  - "evidence_id": string com o UUID da evidência candidata, sem \
colchetes.
  - "node_id": string com o UUID do nó pai, sem colchetes.
  - "rel": string, uma de "elaborate", "question" ou "cancel".
  - "description": string em português do Brasil, uma a duas frases \
curtas. Não repete a evidência nem o nó. Explica de que forma o \
fato reforça, tensiona ou derruba o que o nó afirma. A descrição \
é a manifestação visível da coesão do movimento."""


class Suggestion(BaseModel):
    evidence_id: str
    node_id: str
    rel: str
    description: str = ""

    @model_validator(mode="after")
    def strip_whitespace(self):
        self.evidence_id = self.evidence_id.strip()
        self.node_id = self.node_id.strip()
        self.rel = self.rel.strip()
        self.description = self.description.strip()
        return self


class BuildCaseSuggestions(BaseModel):
    suggestions: list[Suggestion] = Field(default_factory=list)




def _all_tree_evidence_ids(tree: list) -> list[str]:
    ids: list[str] = []
    for node in tree:
        if node.get("type") == "evidence":
            ids.append(node["id"])
        for child in node.get("children", []):
            ids.extend(_all_tree_evidence_ids([child]))
    return ids


def build_prompt(
    schema_context: str, candidate_evidence_xml: str,
) -> str:
    parts = [
        "Estado atual da esquematização:\n\n",
        schema_context,
        "\n\n",
        "Evidências candidatas para posicionamento:\n\n",
        candidate_evidence_xml,
        "\n\n",
        "Analise as evidências candidatas e os slots abertos na "
        "esquematização. Sugira posicionamento apenas quando a relação "
        "entre evidência e nó for genuína e direta. Para cada sugestão, "
        "indique o evidence_id, o node_id do nó pai e a relação "
        "(elaborate, question ou cancel). Produza 0 sugestões se "
        "nenhuma relação clara existir.",
    ]
    return "".join(parts)


def build_messages(
    schema_context: str, candidate_evidence_xml: str,
) -> list:
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=build_prompt(schema_context, candidate_evidence_xml),
        ),
    ]


def call_llm(
    schema_context: str, candidate_evidence_xml: str,
) -> BuildCaseSuggestions:
    structured = get_llm(timeout=60).with_structured_output(
        BuildCaseSuggestions, method="json_schema",
    )
    messages = build_messages(schema_context, candidate_evidence_xml)
    logger.warning(
        "build_case LLM INPUT:\n%s",
        "\n---\n".join(m.content for m in messages),
    )
    result = structured.invoke(messages)
    logger.warning("build_case LLM OUTPUT:\n%s", result)
    return result  # type: ignore[return-value]


def _default_schema_loader(db: Session, workspace_id: uuid.UUID) -> list:
    row = schematization_service.get_or_create(db, workspace_id)
    return row.data


def _default_evidence_loader(db: Session, workspace_id: uuid.UUID) -> list:
    return evidence_service.list_items(db, workspace_id)


def run(
    workspace_id: uuid.UUID,
    llm_caller: Callable[
        [str, str], BuildCaseSuggestions
    ] = call_llm,
    session_factory: Callable[[], Session] = SessionLocal,
    schema_loader: Callable = _default_schema_loader,
    evidence_loader: Callable = _default_evidence_loader,
) -> None:
    db: Session = session_factory()
    try:
        schema_data = schema_loader(db, workspace_id)
        from app.schematization.service import (
            _normalize_data,
            _open_suggestion_slots,
            serialize_xml_suggestions,
            ALL_RELS,
        )
        tree = _normalize_data(schema_data)

        has_nodes = any(
            n.get("type") == "frame" or (
                n.get("type") == "evidence" and not n.get("suggestion")
            )
            for n in tree
        )
        if not has_nodes:
            logger.warning("build_case: no frames/evidence in tree, skipping")
            return

        placed_ids = set(_all_tree_evidence_ids(tree))
        items = evidence_loader(db, workspace_id)

        slots = _open_suggestion_slots(tree)
        if not slots:
            logger.warning("build_case: no open suggestion slots, skipping")
            return

        candidates = [
            item for item in items if str(item.id) not in placed_ids
        ]
        if not candidates:
            logger.warning("build_case: no unplaced candidates, skipping")
            return

        evidence_map = {str(item.id): item.content for item in items}
        schema_context = serialize_xml_suggestions(tree, evidence_map, slots)

        candidate_xml = evidence_service.serialize_xml(candidates)
        result = llm_caller(schema_context, candidate_xml)
        candidate_id_set = {str(item.id) for item in candidates}
        used_slots: set[tuple[str, str]] = set()

        for suggestion in result.suggestions:
            if suggestion.rel not in ALL_RELS:
                continue
            if suggestion.evidence_id not in candidate_id_set:
                continue
            slot_key = (suggestion.node_id, suggestion.rel)
            open_rels = slots.get(suggestion.node_id)
            if not open_rels or suggestion.rel not in open_rels:
                continue
            if slot_key in used_slots:
                continue
            try:
                schematization_service.add_evidence(
                    db,
                    workspace_id,
                    uuid.UUID(suggestion.evidence_id),
                    parent_id=uuid.UUID(suggestion.node_id),
                    rel=suggestion.rel,
                    suggestion=True,
                    description=suggestion.description,
                )
                used_slots.add(slot_key)
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
