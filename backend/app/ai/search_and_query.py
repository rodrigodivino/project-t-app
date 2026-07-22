import json
import logging
import threading
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.settings import AI_EFFORT, AI_MODEL, AI_THINKING, ANTHROPIC_API_KEY
from app.evidence import service as evidence_service
from app.shoebox import service as shoebox_service
from app.sources import service as sources_service
from app.ai import read_and_extract
from app.ai.read_and_extract import GLOSSARY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""\
{GLOSSARY}

Você opera no passo "Search and Filter". Seu papel: gerar consultas \
SQL contra a fonte de dados externa para encontrar dados que possam \
se tornar evidências para elaborar, questionar ou cancelar nós da \
esquematização atual. Os resultados são depositados no shoebox.

Ao escolher consultas, considere lacunas em qualquer uma das três \
relações. Um frame pode precisar de dados que o apoiem (elaborate), \
que o desafiem (question) ou que o invalidem (cancel). Priorize \
consultas que preencham lacunas na cobertura atual da esquematização.

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
- Produza de 0 a 5 consultas SQL SELECT. Na dúvida, produza 1. \
Produza 0 quando o shoebox já cobrir bem a esquematização. Produza \
mais de 1 somente quando múltiplas consultas forem cruciais para \
preencher lacunas distintas na cobertura.
- Prefira consultas que agregam, agrupam, fatiam e cruzam os dados de \
formas úteis: COUNT, GROUP BY, date_trunc, filtros por palavras-chave, \
combinações de colunas. Consultas que revelam padrões são mais valiosas \
do que tabelas brutas de linhas individuais.
- Consultas podem ser agregações ou listagens nominais de linhas \
individuais (ex: mensagens filtradas por palavra-chave). Para \
agregações, produza exatamente uma métrica (COUNT, AVG, SUM, etc.) \
agrupada por uma ou duas colunas categóricas/temporais. Uma dimensão \
é o padrão. Use duas somente quando o cruzamento revela algo que uma \
dimensão sozinha esconde (ex: GROUP BY location, date_trunc('day', \
time) quando a evolução temporal varia por bairro). A métrica pode \
ser expressa como percentual (ex: COUNT(*)::float / SUM(COUNT(*)) \
OVER () * 100 AS pct) quando proporções relativas são mais \
informativas do que valores absolutos.
- Quando a consulta agrupa timestamps (date_trunc, extract ou qualquer \
transformação que colapsa vários instantes em um bucket), formate o \
bucket como rótulo legível no SELECT e ordene pela expressão temporal \
original. Exemplos: \
to_char(date_trunc('day', time), 'Dia DD') AS dia com \
ORDER BY date_trunc('day', time); \
extract(hour FROM time)::int || 'h' AS hora com \
ORDER BY extract(hour FROM time). \
A coluna alias deve ser TEXT, nunca timestamp. O ORDER BY garante \
que as linhas chegam ordenadas no tempo. Nunca use o resultado bruto \
de date_trunc como coluna final. Sempre use HH24 (formato 24 horas) \
em to_char, nunca HH ou HH12.
- Nunca aplique LIMIT a consultas com GROUP BY. O número de linhas \
é determinado pelo número de grupos, não por um teto arbitrário. \
Use LIMIT somente em consultas que listam linhas individuais \
(sem GROUP BY).
- Não gere consultas que dupliquem ou sobreponham substancialmente os \
itens já existentes no shoebox.
- Ao usar ROUND com precisão, converta para numeric antes: \
ROUND((expr)::numeric, 2). PostgreSQL não aceita ROUND(float, int).
- Mantenha as consultas simples e rápidas. Use sempre o nome da tabela \
post_rede_social_himark. Não use CTEs ou subconsultas a menos que \
necessário.
- O campo "explanation" DEVE ser escrito em português brasileiro (pt-BR) \
com acentuação correta. Use o formato "X, para Y" em no máximo 25 \
palavras. X descreve o que os resultados contêm e Y é a razão pela \
qual isso é relevante. Exemplo: "Postagens por bairro por hora, para \
localizar picos de atividade na crise". Sem parênteses, sem apostos. \
O SQL permanece em inglês.

Estratégia de equilíbrio:
- Examine a linha "Cobertura" de cada frame. Priorize consultas que \
preencham lacunas na cobertura de relações. Um frame com 2 \
elaborações e 0 questionamentos precisa de dados que o desafiem, \
não de mais apoio.
- Se uma relação cancel já existe em um nó, busque dados que testem \
se essa invalidação se sustenta ou se ela própria pode ser \
questionada.
- Priorize frames no topo da árvore com menos filhos em vez de nós \
profundos que já possuem cobertura.
- O objetivo é amplitude pela árvore e equilíbrio entre relações, \
não profundidade em um único nó."""


class SearchQuery(BaseModel):
    sql: str
    explanation: str


class SearchQueries(BaseModel):
    queries: list[SearchQuery] = Field(default_factory=list)


def build_prompt(schematization_context: str, existing_items: list[dict]) -> str:
    parts = [
        "Estado atual da esquematização:\n\n",
        schematization_context,
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
        "Produza até 3 consultas SQL SELECT (tipicamente 1 ou 2) contra "
        "post_rede_social_himark que busquem dados capazes de elaborar, "
        "questionar ou cancelar nós da esquematização. Se os itens "
        "existentes já cobrem bem a esquematização, produza menos ou "
        "nenhuma consulta. Priorize equilíbrio entre relações e "
        "cobertura dos nós no topo da árvore."
    )
    return "".join(parts)


def call_llm(
    schematization_context: str, existing_items: list[dict],
) -> SearchQueries:
    llm = ChatAnthropic(
        model_name=AI_MODEL,
        api_key=SecretStr(ANTHROPIC_API_KEY),
        timeout=30,
        stop=None,
        thinking=AI_THINKING,
        effort=AI_EFFORT,
    )
    structured = llm.with_structured_output(SearchQueries)
    result = structured.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=build_prompt(schematization_context, existing_items),
        ),
    ])
    return result  # type: ignore[return-value]


CHART_SYSTEM_PROMPT = """\
Você recebe o SQL de uma consulta, sua explicação e uma amostra dos \
resultados. Produza uma especificação Vega-Lite v5 que visualize \
esses dados de forma clara.

Tipos de coluna (decida pelo valor na amostra, não pelo SQL):
- Datetime: valores TIMESTAMP como "2020-04-06T12:34:00". \
Use type "temporal".
- Quantitativo: métricas numéricas (count, total, avg, pct). \
Use type "quantitative".
- Texto longo (message): não é visualizável. Ignore.
- Dimensões categóricas (strings): escolha entre ordinal e \
nominal conforme a semântica. Exemplos: "Dia 08", "Dia 09" \
são ordinal (sort: null, ordem vem do SQL). Locais como \
"Downtown", "Easton" são nominal.
- Texto livre (message): nunca mapeie para x, y, color ou \
qualquer encoding de eixo. Se houver uma métrica visualizável, \
inclua o texto apenas no encoding de tooltip. Se não houver \
métrica, retorne spec como null.

Como escolher o mark:
- 1 ordinal/nominal + 1 métrica: bar horizontal. \
Dimensão no eixo y (sort: "-x"), métrica no eixo x.
- 1 temporal + 1 métrica: line. Temporal no eixo x, \
métrica no eixo y.
- 2 numéricas sem dimensão categórica: point (dispersão). \
Uma em x, outra em y.
- 2 dimensões + 1 métrica: rect (heatmap). Uma dimensão em x, \
outra em y, métrica no encoding de color com scale contínua.
- O mark line só é válido quando o eixo x é temporal. \
Rótulos de bucket no eixo x recebem bar, nunca line.
- Não use nenhum outro tipo de mark.

Regras:
- Retorne SOMENTE o objeto de especificação Vega-Lite (mark + encoding). \
Não inclua o campo "data" nem "$schema", pois os dados serão injetados \
pelo frontend.
- Use nomes de campo exatamente como aparecem nas colunas dos resultados.
- Inclua "title" curto em português brasileiro.
- Não defina encoding de opacity. Use color livremente quando \
ajudar a distinguir séries ou dimensões.
- Não use nenhum transform. Os dados já chegam agregados e \
recortados pelo SQL. Nada de aggregate, bin, calculate, density, \
extent, filter, flatten, fold, impute, joinaggregate, loess, \
lookup, pivot, quantile, regression, sample, stack, timeUnit, \
window.
- Mantenha a especificação simples. Sem camadas (layer), sem \
composições (concat/facet), sem seleções interativas, sem params.
- Se os resultados contêm apenas 1 linha ou são puramente textuais \
(ex: mensagens sem agregação), retorne spec como null."""


class ChartSpec(BaseModel):
    spec: dict | None = None


def _chart_messages(sql: str, explanation: str, rows: list[dict]) -> list:
    columns = list(rows[0].keys())
    sample = rows[:20]
    prompt = (
        f"SQL: {sql}\n"
        f"Explicação: {explanation}\n"
        f"Colunas: {columns}\n"
        f"Amostra ({len(sample)} de {len(rows)} linhas):\n"
        f"{json.dumps(sample, indent=2, default=str)}"
    )
    return [
        SystemMessage(content=CHART_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]


def _chart_llm() -> Any:
    return ChatAnthropic(
        model_name=AI_MODEL,
        api_key=SecretStr(ANTHROPIC_API_KEY),
        timeout=30,
        stop=None,
        thinking=AI_THINKING,
        effort=AI_EFFORT,
    ).with_structured_output(ChartSpec)


def generate_chart(
    sql: str, explanation: str, rows: list[dict],
) -> dict | None:
    if not ANTHROPIC_API_KEY or not rows:
        return None
    result = _chart_llm().invoke(_chart_messages(sql, explanation, rows))
    return result.spec  # type: ignore[union-attr]


def generate_charts_batch(
    items: list[tuple[str, str, list[dict]]],
) -> list[dict | None]:
    if not ANTHROPIC_API_KEY:
        return [None] * len(items)
    eligible = [
        (i, sql, exp, rows)
        for i, (sql, exp, rows) in enumerate(items)
        if rows
    ]
    if not eligible:
        return [None] * len(items)
    messages = [_chart_messages(sql, exp, rows) for _, sql, exp, rows in eligible]
    raw = _chart_llm().batch(messages)
    specs: list[dict | None] = [None] * len(items)
    for (i, _, _, _), result in zip(eligible, raw):
        specs[i] = result.spec if result else None
    return specs


def _make_serializable(obj):
    if isinstance(obj, Decimal):
        return float(obj)
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
    llm_caller: Callable[[str, list[dict]], SearchQueries] = call_llm,
    session_factory: Callable[[], Session] = SessionLocal,
    items_loader: Callable[..., list[dict]] = shoebox_service.list_summaries_for_prompt,
) -> None:
    db: Session = session_factory()
    try:
        from app.schematization.service import (
            _normalize_data, serialize_for_llm,
        )
        evidence_items = evidence_service.list_items(db, workspace_id)
        evidence_map = {str(item.id): item.content for item in evidence_items}
        tree = _normalize_data(schematization_data)
        schema_context = serialize_for_llm(tree, evidence_map)

        existing = items_loader(db, workspace_id)
        queries = llm_caller(schema_context, existing)
        executed: list[tuple[SearchQuery, list[dict]]] = []
        for q in queries.queries:
            try:
                rows = sources_service.execute_query(db, q.sql)
                executed.append((q, _clean_rows(rows)))
            except Exception:
                logger.exception("query failed: %s", q.sql)
                db.rollback()
        if not executed:
            return
        try:
            charts = generate_charts_batch(
                [(q.sql, q.explanation, clean) for q, clean in executed]
            )
        except Exception:
            logger.exception("batch chart generation failed")
            charts = [None] * len(executed)
        new_ids: list[uuid.UUID] = []
        for (q, clean), chart in zip(executed, charts):
            item = shoebox_service.add_item(
                db, workspace_id, q.sql, q.explanation,
                clean, ai_authored=True, chart_spec=chart,
            )
            new_ids.append(item.id)
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
