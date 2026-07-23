import json
import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai import get_llm
from app.database import SessionLocal
from app.settings import ANTHROPIC_API_KEY
from app.evidence import service as evidence_service
from app.shoebox import service as shoebox_service
from app.sources import service as sources_service
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
- Mensagens com prefixo "re: " são repostagens (compartilhamentos) \
de uma mensagem original. A mensagem original aparece sem o prefixo. \
Quando várias contas publicam o mesmo texto com "re: ", trata-se de \
difusão viral, não de postagens independentes.

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
- Quando a consulta agrupa timestamps com date_trunc, mantenha o \
resultado como timestamp no SELECT e ordene por ele. Exemplo: \
date_trunc('hour', time) AS hora com ORDER BY 1. Não aplique \
to_char nem cast para TEXT sobre date_trunc. \
Quando usar extract (hour, dow), concatene uma unidade legível: \
extract(hour FROM time)::int || 'h' AS hora com \
ORDER BY extract(hour FROM time).
- Toda expressão não-agregada no SELECT deve aparecer no GROUP BY \
(ou ser derivada dele). Correto: GROUP BY date_trunc('day', time) \
com date_trunc('day', time) AS dia no SELECT. Incorreto: \
GROUP BY date_trunc('day', time) com extract(day FROM time) \
no SELECT.
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
não profundidade em um único nó.

Formato de saída:
- "queries": lista de objetos, cada um com:
  - "sql": string com a consulta SQL SELECT. Em inglês.
  - "explanation": string em pt-BR, formato "X, para Y" (máx 25 \
palavras). X descreve o conteúdo dos resultados, Y é a relevância \
para a análise."""


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
    structured = get_llm().with_structured_output(SearchQueries, method="json_schema")
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
- Datetime: valores ISO como "2020-04-06T12:00:00" (incluindo \
timestamps arredondados por date_trunc). Use type "temporal".
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
- 1 temporal + 1 categórica + 1 métrica: line com color. \
Temporal no eixo x, métrica no eixo y, categórica no encoding \
color (type nominal).
- 2 numéricas sem dimensão categórica: point (dispersão).
- 2 dimensões não-temporais + 1 métrica: rect (heatmap).
- Não use nenhum outro tipo de mark.

Regras:
- Retorne a especificação Vega-Lite (mark + encoding) como uma string \
JSON. Não inclua o campo "data" nem "$schema", pois os dados serão \
injetados pelo frontend.
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
(ex: mensagens sem agregação), retorne spec como null.

Formato de saída:
- "explanation": raciocínio curto (1-2 frases) sobre qual mark e \
encoding usar e por quê. Serve para melhorar a qualidade da spec. \
Escreva antes da spec.
- "spec": string JSON com a especificação Vega-Lite (mark + encoding \
+ title). Sem "data", sem "$schema".

Exemplos de especificação para cada tipo de mark:

Bar horizontal (1 dimensão + 1 métrica):
{"mark": {"type": "bar"}, "encoding": {"y": {"field": "location", \
"type": "nominal", "sort": "-x"}, "x": {"field": "total", \
"type": "quantitative"}}, "title": "Total por bairro"}

Line (1 temporal + 1 métrica):
{"mark": {"type": "line"}, "encoding": {"x": {"field": "time", \
"type": "temporal"}, "y": {"field": "total", \
"type": "quantitative"}}, "title": "Volume ao longo do tempo"}

Line com séries (1 temporal + 1 categórica + 1 métrica):
{"mark": {"type": "line"}, "encoding": {"x": {"field": "hora", \
"type": "temporal"}, "y": {"field": "total", \
"type": "quantitative"}, "color": {"field": "location", \
"type": "nominal"}}, "title": "Volume por bairro ao longo do tempo"}

Point / dispersão (2 numéricas):
{"mark": {"type": "point"}, "encoding": {"x": {"field": "metrica_a", \
"type": "quantitative"}, "y": {"field": "metrica_b", \
"type": "quantitative"}}, "title": "Dispersão A vs B"}

Rect / heatmap (2 dimensões + 1 métrica):
{"mark": {"type": "rect"}, "encoding": {"x": {"field": "hora", \
"type": "ordinal", "sort": null}, "y": {"field": "location", \
"type": "nominal"}, "color": {"field": "total", \
"type": "quantitative"}}, "title": "Atividade por bairro e hora"}"""


class ChartSpec(BaseModel):
    explanation: str = ""
    spec: str | None = None


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
    return get_llm().with_structured_output(ChartSpec, method="json_schema")


def _parse_spec(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return None
        if not parsed.get("encoding") and not parsed.get("layer"):
            return None
        return parsed
    except (json.JSONDecodeError, TypeError):
        return None


def generate_chart(
    sql: str, explanation: str, rows: list[dict],
) -> dict | None:
    if not ANTHROPIC_API_KEY or not rows:
        return None
    result = _chart_llm().invoke(_chart_messages(sql, explanation, rows))
    return _parse_spec(result.spec)  # type: ignore[union-attr]


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
        specs[i] = _parse_spec(result.spec) if result else None
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
        for (q, clean), chart in zip(executed, charts):
            shoebox_service.add_item(
                db, workspace_id, q.sql, q.explanation,
                clean, ai_authored=True, chart_spec=chart,
            )
    except Exception:
        logger.exception(
            "search_and_query failed for workspace %s", workspace_id
        )
    finally:
        db.close()
