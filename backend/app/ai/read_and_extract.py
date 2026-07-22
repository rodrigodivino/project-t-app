import json
import logging
import threading
import uuid
from typing import Callable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.evidence import service as evidence_service
from app.schematization import service as schematization_service
from app.settings import ANTHROPIC_API_KEY
from app.shoebox import service as shoebox_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Você opera dentro de um framework de sensemaking, no passo \
"Read and Extract". Os construtos do framework são: fonte de \
dados externa, shoebox, snippets, arquivo de evidências, frames, \
esquematização e história.

Seu papel: ler um item do shoebox e extrair snippets factuais \
para depositar nos arquivos de evidência. Snippets são \
proposições concisas, bem formadas, significativas e precisas \
extraídas dos dados subjacentes, sem interpretações, inferências, \
deduções, julgamentos, vieses ou qualquer outra conclusão subjetiva.

Regras:
- Produza ATÉ 3 snippets para o item do shoebox fornecido. \
Se os dados não contêm informação relevante para a esquematização, \
produza menos ou nenhum snippet.
- Cada snippet deve ser uma observação factual e objetiva dos dados, \
não uma interpretação ou inferência.
- Cada snippet deve referenciar as linhas específicas do resultado \
que fundamentam a observação (campo "rows" com índices base-0).
- Não produza snippets que dupliquem ou sobreponham substancialmente \
as evidências já existentes nos arquivos de evidência.
- O campo "content" DEVE ser escrito em português brasileiro (pt-BR) \
com acentuação correta. Descreva o fato observado nos dados de forma \
objetiva e concisa."""


class Snippet(BaseModel):
    content: str
    rows: list[int]


class ExtractionResult(BaseModel):
    snippets: list[Snippet] = Field(default_factory=list)


def build_prompt(
    schematization_data: dict,
    evidence_titles: list[str],
    shoebox_item: dict,
) -> str:
    parts = [
        "Estado atual da esquematização:\n\n",
        json.dumps(schematization_data, indent=2, default=str),
        "\n\n",
    ]
    if evidence_titles:
        parts.append(
            "Snippets já existentes nos arquivos de evidência "
            "(evite duplicar):\n\n"
        )
        for i, title in enumerate(evidence_titles, 1):
            parts.append(f"  {i}. {title}\n")
        parts.append("\n")
    else:
        parts.append("Os arquivos de evidência estão vazios.\n\n")

    parts.append("Item do shoebox para leitura e extração:\n\n")
    parts.append(f"Consulta: {shoebox_item['query']}\n")
    parts.append(f"Explicação: {shoebox_item['explanation']}\n")
    result = shoebox_item["result"]
    parts.append(f"Resultado ({len(result)} linhas):\n")
    parts.append(json.dumps(result, indent=2, default=str))
    parts.append("\n\n")
    parts.append(
        "Extraia até 3 snippets factuais relevantes para a esquematização "
        "a partir dos dados deste item. Para cada snippet, indique quais "
        "linhas do resultado fundamentam a observação (índices base-0)."
    )
    return "".join(parts)


def build_messages(
    schematization_data: dict,
    evidence_titles: list[str],
    shoebox_item: dict,
) -> list:
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=build_prompt(schematization_data, evidence_titles, shoebox_item)
        ),
    ]


def call_llm_batch(inputs: list[list]) -> list[ExtractionResult]:
    llm = ChatAnthropic(
        model_name="claude-sonnet-5",
        api_key=SecretStr(ANTHROPIC_API_KEY),
        timeout=60,
        stop=None,
    )
    structured = llm.with_structured_output(ExtractionResult)
    return structured.batch(inputs)


def _default_schema_loader(db: Session, workspace_id: uuid.UUID) -> dict:
    row = schematization_service.get_or_create(db, workspace_id)
    return row.data


def _default_shoebox_loader(db: Session, workspace_id: uuid.UUID) -> list:
    return shoebox_service.list_items(db, workspace_id)


def _default_shoebox_getter(db: Session, item_id: uuid.UUID):
    return shoebox_service.get_item(db, item_id)


def _default_evidence_titles_loader(
    db: Session, workspace_id: uuid.UUID,
) -> list[str]:
    items = evidence_service.list_items(db, workspace_id)
    return [item.content for item in items]


def _item_to_dict(item) -> dict:
    return {
        "query": item.query,
        "explanation": item.explanation,
        "result": item.result,
    }


def run(
    workspace_id: uuid.UUID,
    shoebox_ids: list[uuid.UUID] | None = None,
    llm_caller: Callable[[list[list]], list[ExtractionResult]] = call_llm_batch,
    session_factory: Callable[[], Session] = SessionLocal,
    schema_loader: Callable = _default_schema_loader,
    shoebox_loader: Callable = _default_shoebox_loader,
    shoebox_getter: Callable = _default_shoebox_getter,
    evidence_titles_loader: Callable = _default_evidence_titles_loader,
) -> None:
    db: Session = session_factory()
    try:
        schema_data = schema_loader(db, workspace_id)
        if not schema_data.get("evidence"):
            return

        evidence_titles = evidence_titles_loader(db, workspace_id)

        if shoebox_ids is not None:
            items = [shoebox_getter(db, sid) for sid in shoebox_ids]
            items = [i for i in items if i is not None]
        else:
            items = shoebox_loader(db, workspace_id)

        if not items:
            return

        inputs = [
            build_messages(schema_data, evidence_titles, _item_to_dict(item))
            for item in items
        ]

        results = llm_caller(inputs)

        for item, extraction in zip(items, results):
            for snippet in extraction.snippets:
                try:
                    evidence_service.add_item(
                        db,
                        workspace_id,
                        item.id,
                        snippet.content,
                        snippet.rows,
                        ai_authored=True,
                    )
                except Exception:
                    logger.exception(
                        "failed to add snippet for shoebox %s", item.id
                    )
                    db.rollback()
    except Exception:
        logger.exception(
            "read_and_extract failed for workspace %s", workspace_id
        )
    finally:
        db.close()


def fire(
    workspace_id: uuid.UUID,
    shoebox_ids: list[uuid.UUID] | None = None,
) -> None:
    thread = threading.Thread(
        target=run,
        args=(workspace_id, shoebox_ids),
        daemon=True,
    )
    thread.start()
