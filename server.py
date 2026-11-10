"""FastAPI entry point and background update orchestration."""
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import threading
import time

import MetaTrader5 as mt5
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from backend.ai_analysis import analyze_news_and_events, relevant_events
from backend.indicators import analyze_indicators
from backend.news_fetch import fetch_calendar_events, fetch_news

SYMBOL = os.getenv("SYMBOL", "XAUUSD.m")
TIMEFRAMES = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
AI_REFRESH_SECONDS = 900

app_state = {"tech": {}, "price": None, "events": [], "news": [], "ai": None, "updated": {},
     "ai_status": {"state": "starting"}}


def update_technical_data():
    mt5.initialize()
    mt5.symbol_select(SYMBOL, True)
    while True:
        try:
            tech = {}
            for name, tf in TIMEFRAMES.items():
                rates = mt5.copy_rates_from_pos(SYMBOL, tf, 1, 300)
                if rates is not None and len(rates) > 210:
                    tech[name] = analyze_indicators(pd.DataFrame(rates))
            tick = mt5.symbol_info_tick(SYMBOL)
            app_state["tech"], app_state["price"] = tech, (tick.bid if tick else None)
            app_state["updated"]["tech"] = time.time()
        except Exception as e:
            app_state["updated"]["tech_error"] = str(e)
        time.sleep(10)


def update_calendar():
    while True:
        try:
            app_state["events"] = fetch_calendar_events()
            app_state["updated"]["calendar"] = time.time()
            app_state["updated"].pop("cal_error", None)
        except Exception as e:
            app_state["updated"]["cal_error"] = str(e)
        time.sleep(300)

def update_news_and_ai():
    last_key = None
    while True:
        try:
            items = fetch_news()
            app_state["news"] = items[:20]
            app_state["updated"]["news"] = time.time()
            events = relevant_events(app_state["events"])
            # Inclui resultados e previsão: a IA deve ser atualizada quando o calendário mudar.
            key = json.dumps([items[:10], events], ensure_ascii=False, sort_keys=True)
            if not os.getenv("OPENAI_API_KEY"):
                app_state["ai_status"] = {"state": "disabled"}
            elif key != last_key or time.time() - app_state["updated"].get("ai", 0) >= AI_REFRESH_SECONDS:
                app_state["ai_status"] = {"state": "loading"}
                result = analyze_news_and_events(items[:10], events)
                result["eventos_base"] = events
                result["noticias_base"] = items[:10]
                app_state["ai"] = result
                app_state["updated"]["ai"] = time.time()
                app_state["updated"].pop("news_error", None)
                last_key = key
                app_state["ai_status"] = {"state": "ready", "next_update": app_state["updated"]["ai"] + AI_REFRESH_SECONDS}
        except Exception as e:
            app_state["updated"]["news_error"] = str(e)
            app_state["ai_status"] = {"state": "error"}
        time.sleep(300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for worker in (update_technical_data, update_calendar, update_news_and_ai):
        threading.Thread(target=worker, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/api/state")
def get_state():
    return JSONResponse({**app_state, "symbol": SYMBOL, "now": int(time.time() * 1000)})


@app.get("/")
def main_interface():
    return FileResponse(BASE_DIR / "frontend" / "index.html")
