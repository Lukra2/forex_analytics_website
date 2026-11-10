"""Select economic events and request the AI analysis."""
import datetime as dt
import json
import os
import time
from typing import Literal

from pydantic import BaseModel


class NewsItemAnalysis(BaseModel):
    n: int
    impacto: Literal["Altista", "Baixista", "Neutro"]
    nota: str


class EventScenario(BaseModel):
    resultado: str
    impacto: Literal["Altista", "Baixista", "Neutro", "Indefinido"]
    explicacao: str


class EventAnalysis(BaseModel):
    id: int
    leitura: str
    cenarios: list[EventScenario]


class MarketAnalysis(BaseModel):
    vies: Literal["Altista", "Baixista", "Neutro"]
    confianca: int
    resumo: str
    motivo: str
    itens: list[NewsItemAnalysis]
    eventos: list[EventAnalysis]


def relevant_events(events, now_ms=None):
    """Eventos recentes e próximos, limitados para manter a análise legível."""
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    recent = [e for e in events if now_ms - 48 * 3600000 <= e["ts"] <= now_ms]
    upcoming = [e for e in events if now_ms < e["ts"] <= now_ms + 72 * 3600000]
    return recent[-8:] + upcoming[:8]


def analyze_news_and_events(items, events):
    from openai import OpenAI
    heads = "\n".join(f"{i+1}. {x['title']}" for i, x in enumerate(items))
    event_data = [{"id": i + 1, **event,
                   "data_utc": dt.datetime.fromtimestamp(event["ts"] / 1000, dt.timezone.utc).isoformat()}
                  for i, event in enumerate(events)]
    prompt = (
        "Você analisa notícias e eventos para um trader de ouro (XAUUSD) com termos simples e fáceis para compreensão de todos os públicos. Responda SOMENTE JSON válido, sem markdown:\n"
        '{"vies":"Altista|Baixista|Neutro","confianca":0-100,"resumo":"2 frases em português",'
        '"motivo":"cadeia causal curta incluindo eventos USD",'
        '"itens":[{"n":1,"impacto":"Altista|Baixista|Neutro","nota":"1 linha"}],'
        '"eventos":[{"id":1,"leitura":"interpretação breve dos dados disponíveis",'
        '"cenarios":[{"resultado":"resultado possível", "impacto":"Altista|Baixista|Neutro|Indefinido",'
        '"explicacao":"efeito provável no XAUUSD e motivo"}]}]}\n'
        "Inclua um objeto eventos para cada evento fornecido, usando o id exato. Para indicadores numéricos, "
        "cubra acima, em linha e abaixo da previsão; para decisões, discursos e eventos sem previsão numérica, "
        "use desfechos apropriados ao evento, sem inventar valores. Compare actual com forecast somente quando ambos "
        "estiverem disponíveis. Se actual estiver ausente, diga que o resultado não está disponível, mesmo para "
        "eventos passados; nunca o invente. Trate movimentos como hipóteses condicionais, sem metas de preço ou "
        "certeza, considerando possíveis reações já precificadas. Responda em português. "
        "Considere dólar, juros, Fed, inflação e geopolítica.\nManchetes:\n" + heads +
        "\nEventos USD (horários em UTC; actual é resultado divulgado quando disponível):\n" +
        json.dumps(event_data, ensure_ascii=False))
    response = OpenAI(timeout=90.0, max_retries=1).responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
        input=[{"role": "user", "content": prompt}],
        text_format=MarketAnalysis,
        max_output_tokens=10000,
        store=False,
    )
    if response.output_parsed is None:
        raise ValueError("A OpenAI não retornou uma análise completa no formato esperado.")
    return response.output_parsed.model_dump()

