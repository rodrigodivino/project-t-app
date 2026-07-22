import json
import logging
import threading
import uuid
from datetime import date, datetime
from typing import Callable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.settings import ANTHROPIC_API_KEY
from app.shoebox import service as shoebox_service
from app.sources import service as sources_service
from app.ai import read_and_extract

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Você opera dentro de um framework de sensemaking, no passo \
"Search and Filter". Os construtos do framework são: fonte de \
dados externa, shoebox, snippets, arquivo de evidências, frames, \
esquematização e história.

Seu papel: consultar a fonte de dados externa (uma tabela PostgreSQL) \
e produzir resultados para depositar no shoebox. Suas consultas devem \
buscar relevância para a esquematização atual, que contém frames \
(perspectivas interpretativas), referências de evidência e relações \
entre eles.

A fonte de dados externa é a tabela post_rede_social_himark, contendo \
postagens de redes sociais do dataset VAST 2019 MC3, representando a \
cidade fictícia de St. Himark durante uma crise. O esquema da tabela:

  id       INTEGER  PRIMARY KEY (auto-increment)
  time     TIMESTAMP  (de 2020-04-06 00:00 até 2020-04-10 11:59)
  location TEXT
  account  TEXT
  message  TEXT

Valores possíveis de location: Broadview, Chapparal, Cheddarford, \
Downtown, Easton, East Parton, <Location with-held due to contract>, \
Northwest, Oak Willow, Old Town, Palace Hills, Pepper Mill, Safe Town, \
Scenic Vista, Southton, Southwest, Terrapin Springs, UNKNOWN, Weston, \
West Parton, Wilson Forest.

Características importantes dos dados:
- As mensagens são escritas em inglês.
- As postagens podem conter conteúdo não confiável, automatizado ou \
gerado por bots.

Regras:
- Produza ATÉ 3 consultas SQL SELECT. Se a esquematização já estiver \
bem coberta pelos itens existentes no shoebox, produza menos ou nenhuma.
- Prefira consultas que agregam, agrupam, fatiam e cruzam os dados de \
formas úteis: COUNT, GROUP BY, date_trunc, filtros por palavras-chave, \
combinações de colunas. Consultas que revelam padrões são mais valiosas \
do que tabelas brutas de linhas individuais.
- Limite os resultados com LIMIT para evitar tabelas gigantes. Use \
LIMIT em consultas de linhas individuais. Agregações naturalmente \
compactas (poucos grupos) não precisam de LIMIT.
- Não gere consultas que dupliquem ou sobreponham substancialmente os \
itens já existentes no shoebox.
- Mantenha as consultas simples e rápidas. Use sempre o nome da tabela \
post_rede_social_himark. Não use CTEs ou subconsultas a menos que \
necessário.
- O campo "explanation" DEVE ser escrito em português brasileiro (pt-BR) \
com acentuação correta. Use o formato "X, para Y", onde X descreve o \
que os resultados contêm e Y é a razão pela qual isso é relevante \
para a esquematização. Exemplo: "Contagem de postagens por bairro \
por hora, para identificar onde a atividade concentrou durante a crise". \
O SQL permanece em inglês."""


class SearchQuery(BaseModel):
    sql: str
    explanation: str


class SearchQueries(BaseModel):
    queries: list[SearchQuery] = Field(default_factory=list)


def build_prompt(schematization_data: dict, existing_items: list[dict]) -> str:
    parts = [
        "Estado atual da esquematização:\n\n",
        json.dumps(schematization_data, indent=2),
        "\n\n",
    ]
    if existing_items:
        parts.append(
            "O shoebox já contém os seguintes itens "
            "(consulta + explicação + amostra de linhas). "
            "Evite gerar consultas que dupliquem essa cobertura:\n\n"
        )
        for i, item in enumerate(existing_items, 1):
            parts.append(f"--- Item {i} ---\n")
            parts.append(f"Consulta: {item['query']}\n")
            parts.append(f"Explicação: {item['explanation']}\n")
            if item.get("sample_rows"):
                parts.append(
                    f"Amostra: {json.dumps(item['sample_rows'], indent=2, default=str)}\n"
                )
            parts.append("\n")
    else:
        parts.append("O shoebox está vazio.\n\n")

    parts.append(
        "Produza até 3 consultas SQL SELECT contra post_rede_social_himark "
        "que ajudem o analista a explorar dados relevantes para esta "
        "esquematização. Se os itens existentes já cobrem bem a "
        "esquematização, produza menos ou nenhuma consulta."
    )
    return "".join(parts)


def call_llm(
    schematization_data: dict, existing_items: list[dict],
) -> SearchQueries:
    llm = ChatAnthropic(
        model_name="claude-sonnet-5",
        api_key=SecretStr(ANTHROPIC_API_KEY),
        timeout=30,
        stop=None,
    )
    structured = llm.with_structured_output(SearchQueries)
    result = structured.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_prompt(schematization_data, existing_items)),
    ])
    return result  # type: ignore[return-value]


CHART_SYSTEM_PROMPT = """\
Você recebe o SQL de uma consulta, sua explicação e uma amostra dos \
resultados. Produza uma especificação Vega-Lite v5 que visualize \
esses dados de forma clara.

Regras:
- Retorne SOMENTE o objeto de especificação Vega-Lite (mark + encoding + params). \
Não inclua o campo "data" nem "$schema", pois os dados serão injetados \
pelo frontend.
- Escolha o tipo de mark mais adequado: bar para contagens e agregações, \
line para séries temporais, point para dispersão.
- Use nomes de campo exatamente como aparecem nas colunas dos resultados.
- Inclua "title" curto em português brasileiro.
- Se os dados tiverem campos temporais (time, date, hora), use \
encoding temporal.
- Pode usar encoding de color livremente (ex: por categoria).
- Não defina encoding de opacity. O frontend controla opacity para \
seleção de dados.
- Inclua um "params" com uma seleção de brush para permitir ao \
usuário selecionar dados interativamente. Use o nome "brush" e \
tipo "interval". Vincule aos eixos apropriados: apenas x para \
séries temporais e barras, x e y para dispersão. Não conecte o \
brush a nenhum encoding condicional, o frontend cuida disso.
- Mantenha a especificação simples. Sem camadas (layer), sem \
composições (concat/facet).
- Se os resultados contêm apenas 1 linha ou são puramente textuais \
(ex: mensagens sem agregação), retorne spec como null."""


class ChartSpec(BaseModel):
    spec: dict | None = None


def generate_chart(
    sql: str, explanation: str, rows: list[dict],
) -> dict | None:
    if not ANTHROPIC_API_KEY:
        return None
    if not rows:
        return None
    columns = list(rows[0].keys())
    sample = rows[:20]
    llm = ChatAnthropic(
        model_name="claude-sonnet-5",
        api_key=SecretStr(ANTHROPIC_API_KEY),
        timeout=30,
        stop=None,
    )
    structured = llm.with_structured_output(ChartSpec)
    prompt = (
        f"SQL: {sql}\n"
        f"Explicação: {explanation}\n"
        f"Colunas: {columns}\n"
        f"Amostra ({len(sample)} de {len(rows)} linhas):\n"
        f"{json.dumps(sample, indent=2, default=str)}"
    )
    result = structured.invoke([
        SystemMessage(content=CHART_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    return result.spec  # type: ignore[union-attr]


def _make_serializable(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    return obj


def _clean_rows(rows: list[dict]) -> list[dict]:
    return [{k: _make_serializable(v) for k, v in row.items()} for row in rows]


def run(
    workspace_id: uuid.UUID,
    schematization_data: dict,
    llm_caller: Callable[[dict, list[dict]], SearchQueries] = call_llm,
    session_factory: Callable[[], Session] = SessionLocal,
    items_loader: Callable[..., list[dict]] = shoebox_service.list_summaries_for_prompt,
) -> None:
    db: Session = session_factory()
    try:
        existing = items_loader(db, workspace_id)
        queries = llm_caller(schematization_data, existing)
        new_ids: list[uuid.UUID] = []
        for q in queries.queries:
            try:
                rows = sources_service.execute_query(db, q.sql)
                clean = _clean_rows(rows)
                chart = None
                try:
                    chart = generate_chart(q.sql, q.explanation, clean)
                except Exception:
                    logger.exception("chart generation failed: %s", q.sql)
                item = shoebox_service.add_item(
                    db, workspace_id, q.sql, q.explanation,
                    clean, ai_authored=True, chart_spec=chart,
                )
                new_ids.append(item.id)
            except Exception:
                logger.exception("query failed: %s", q.sql)
                db.rollback()
        if new_ids and ANTHROPIC_API_KEY:
            read_and_extract.fire(workspace_id, shoebox_ids=new_ids)
    except Exception:
        logger.exception(
            "search_and_query failed for workspace %s", workspace_id
        )
    finally:
        db.close()


def fire(workspace_id: uuid.UUID, schematization_data: dict) -> None:
    thread = threading.Thread(
        target=run,
        args=(workspace_id, schematization_data),
        daemon=True,
    )
    thread.start()
