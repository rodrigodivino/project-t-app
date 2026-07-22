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
from app.settings import AI_EFFORT, AI_MODEL, AI_THINKING, ANTHROPIC_API_KEY
from app.shoebox import service as shoebox_service

logger = logging.getLogger(__name__)

GLOSSARY = """\
Glossário do framework de sensemaking:
- Fonte de dados externa: repositório de dados sob análise.
- Shoebox: subconjunto da fonte relevante para a análise atual. \
Cada item contém uma consulta SQL, uma explicação e uma tabela de \
resultados.
- Snippet: proposição factual curta extraída dos dados, sem \
interpretação ou inferência. Snippets são os blocos de construção \
das evidências.
- Arquivo de evidências: conjunto de snippets extraídos do shoebox.
- Frame: perspectiva, hipótese ou enquadramento criado pelo analista. \
Frames são exclusivamente humanos.
- Esquematização: representação externa do entendimento do analista, \
organizada como árvore de frames e evidências com relações entre eles.
- Relações entre evidência e nó pai:
  - elaborate: a evidência apoia ou detalha o nó
  - question: a evidência questiona ou desafia o nó
  - cancel: a evidência invalida o nó
- História: articulação textual da esquematização para comunicação."""

SYSTEM_PROMPT = f"""\
{GLOSSARY}

Você opera no passo "Read and Extract". Seu papel: ler um item do \
shoebox e extrair snippets factuais que possam servir como evidências \
para elaborar, questionar ou cancelar nós da esquematização atual.

Ao extrair snippets, considere se os dados contêm fatos que poderiam \
se relacionar com os nós da esquematização em qualquer uma dessas \
três formas. Um fato que questiona ou invalida um frame é tão valioso \
quanto um que o apoia. Os snippets são auto-contidos e não mencionam \
a esquematização nem os frames em seu texto.

Regras:
- Produza de 0 a 5 snippets para o item do shoebox fornecido. \
Na dúvida, produza 1. Produza 0 quando os dados já estiverem \
cobertos pelas evidências existentes. Produza mais de 1 somente \
quando múltiplas observações forem cruciais para a análise.
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
com acentuação correta. Cada snippet é UMA ÚNICA frase curta (máximo \
20 palavras) que afirma um fato observável nos dados. Sem parênteses, \
sem apostos explicativos, sem enumerações de valores. Se a frase \
precisa de uma vírgula além de conectivos simples, ela é longa demais.

Estratégia de equilíbrio:
- Examine a linha "Cobertura" de cada frame. Quando um nó tem várias \
elaborações e nenhum questionamento ou cancelamento, priorize a \
extração de fatos que possam questionar ou cancelar esse nó.
- Quando uma relação cancel já existe em um nó, procure fatos que \
testem se essa invalidação se sustenta.
- Priorize snippets relevantes para frames no topo da árvore com \
menos filhos."""


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
            "Snippets já existentes nos arquivos de evidência (evite duplicar):\n\n"
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
    parts.append(f"Resultado ({len(result)} linhas, índice base-0):\n")
    indexed = [{"_index": i, **row} for i, row in enumerate(result)]
    parts.append(json.dumps(indexed, indent=2, default=str))
    parts.append("\n\n")
    parts.append(
        "Extraia de 0 a 5 snippets factuais que elaborem, questionem ou "
        "cancelem nós da esquematização. Para cada snippet, indique quais "
        "linhas do resultado fundamentam a observação (índices base-0). "
        "Na dúvida, produza 1. Priorize equilíbrio entre relações e "
        "cobertura dos nós no topo da árvore."
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
                schematization_context,
                evidence_titles,
                shoebox_item,
            )
        ),
    ]


def call_llm_batch(inputs: list[list]) -> list[ExtractionResult]:
    llm = ChatAnthropic(
        model_name=AI_MODEL,
        api_key=SecretStr(ANTHROPIC_API_KEY),
        timeout=60,
        stop=None,
        thinking=AI_THINKING,
        effort=AI_EFFORT,
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
            _normalize_data,
            serialize_for_llm,
        )

        tree = _normalize_data(schema_data)

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
            logger.warning("read_and_extract EARLY EXIT: no shoebox items")
            return

        inputs = [
            build_messages(schema_context, evidence_titles, _item_to_dict(item))
            for item in items
        ]

        logger.warning("read_and_extract LLM input count=%d, first=%s", len(inputs), inputs[0] if inputs else "EMPTY")
        results = llm_caller(inputs)
        logger.warning("read_and_extract LLM results count=%d, results=%s", len(results), results)

        new_evidence_ids: list[uuid.UUID] = []
        for item, extraction in zip(items, results):
            for snippet in extraction.snippets:
                try:
                    ev = evidence_service.add_item(
                        db,
                        workspace_id,
                        item.id,
                        snippet.content,
                        snippet.rows,
                        ai_authored=True,
                    )
                    new_evidence_ids.append(ev.id)
                except Exception:
                    logger.exception("failed to add snippet for shoebox %s", item.id)
                    db.rollback()
        if new_evidence_ids and ANTHROPIC_API_KEY:
            from app.ai import build_case

            build_case.fire(workspace_id, evidence_ids=new_evidence_ids)
    except Exception:
        logger.exception("read_and_extract failed for workspace %s", workspace_id)
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
