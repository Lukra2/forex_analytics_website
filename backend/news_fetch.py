"""Fetch the economic calendar and RSS headlines."""
import datetime as dt

import feedparser
import requests

NEWS_FEEDS = [
    "https://news.google.com/rss/search?q=gold+price+fed+dollar&hl=en-US&gl=US&ceid=US:en",
    "https://www.fxstreet.com/rss/news",
]
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


def fetch_calendar_events():
    response = requests.get(CALENDAR_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    events = response.json()
    return sorted(
                [{"title": e["title"], "impact": e["impact"], "forecast": e.get("forecast"),
                  "previous": e.get("previous"), "actual": e.get("actual"),
                  "ts": int(dt.datetime.fromisoformat(e["date"]).timestamp() * 1000)}
                 for e in events if e["country"] == "USD" and e["impact"] in ("High", "Medium")],
                key=lambda e: e["ts"])


def fetch_news():
    articles = []
    for url in NEWS_FEEDS:
        for entry in feedparser.parse(url).entries[:12]:
            articles.append({"title": entry.title, "link": entry.link, "src": url.split("/")[2]})
    return articles[:20]
