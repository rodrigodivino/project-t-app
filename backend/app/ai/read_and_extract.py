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
from app.settings import AI_MODEL, ANTHROPIC_API_KEY
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
- Produza ATÉ 2 snippets para o item do shoebox fornecido. \
Na maioria dos casos, 0 ou 1 snippet é suficiente. Produza 2 somente \
quando os dados são ricos e contêm observações claramente distintas. \
Se os dados não contêm informação relevante para a esquematização, \
produza nenhum snippet.
- Cada snippet deve ser uma observação factual e objetiva dos dados, \
não uma interpretação ou inferência.
- Cada snippet deve referenciar as linhas específicas do resultado \
que fundamentam a observação (campo "rows" com índices base-0).
- As linhas selecionadas devem ser essenciais para o snippet, não \
menções incidentais. Selecione linhas que exibem o padrão descrito: \
os maiores valores, os outliers, os que crescem ou declinam, os que \
contrastam entre si. Se o snippet descreve um padrão que abrange \
todos os dados, inclua todas as linhas, mas reserve isso para \
padrões genuinamente globais. Nunca selecione linhas apenas porque \
elas existem nos resultados. A seleção deve permitir ao leitor \
verificar a afirmação do snippet olhando somente as linhas indicadas.
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
    schematization_context: str,
    evidence_titles: list[str],
    shoebox_item: dict,
) -> str:
    parts = [
        "Estado atual da esquematização:\n\n",
        schematization_context,
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
        "Extraia até 2 snippets factuais relevantes para a esquematização "
        "a partir dos dados deste item (tipicamente 0 ou 1). Para cada "
        "snippet, indique quais linhas do resultado fundamentam a "
        "observação (índices base-0)."
    )
    return "".join(parts)


def build_messages(
    schematization_context: str,
    evidence_titles: list[str],
    shoebox_item: dict,
) -> list:
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=build_prompt(
                schematization_context, evidence_titles, shoebox_item,
            )
        ),
    ]


def call_llm_batch(inputs: list[list]) -> list[ExtractionResult]:
    llm = ChatAnthropic(
        model_name=AI_MODEL,
        api_key=SecretStr(ANTHROPIC_API_KEY),
        timeout=60,
        stop=None,
    )
    structured = llm.with_structured_output(ExtractionResult)
    return structured.batch(inputs)


def _default_schema_loader(db: Session, workspace_id: uuid.UUID) -> list:
    row = schematization_service.get_or_create(db, workspace_id)
    return row.data


def _default_shoebox_loader(db: Session, workspace_id: uuid.UUID) -> list:
    return shoebox_service.list_items(db, workspace_id)


def _default_shoebox_getter(db: Session, item_id: uuid.UUID):
    return shoebox_service.get_item(db, item_id)


def _default_evidence_loader(db: Session, workspace_id: uuid.UUID) -> list:
    return evidence_service.list_items(db, workspace_id)


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
    evidence_loader: Callable = _default_evidence_loader,
) -> None:
    db: Session = session_factory()
    try:
        schema_data = schema_loader(db, workspace_id)
        from app.schematization.service import (
            _all_evidence_ids, _normalize_data, serialize_for_llm,
        )
        tree = _normalize_data(schema_data)
        if not _all_evidence_ids(tree):
            return

        evidence_items = evidence_loader(db, workspace_id)
        evidence_map = {str(item.id): item.content for item in evidence_items}
        evidence_titles = [item.content for item in evidence_items]
        schema_context = serialize_for_llm(tree, evidence_map)

        if shoebox_ids is not None:
            items = [shoebox_getter(db, sid) for sid in shoebox_ids]
            items = [i for i in items if i is not None]
        else:
            items = shoebox_loader(db, workspace_id)

        if not items:
            return

        inputs = [
            build_messages(schema_context, evidence_titles, _item_to_dict(item))
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
