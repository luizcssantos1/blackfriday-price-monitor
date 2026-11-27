"""Discover candidate offers using the official Tavily Search API."""
import os
import re
import json
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlsplit
from pathlib import Path
import requests

BRANDS = re.compile(r"\b(Electrolux|Midea|LG|Samsung|Brastemp)\b", re.I)
MODEL = re.compile(r"side[ -]by[ -]side", re.I)
VOLTAGE = re.compile(r"\b220\s*v\b", re.I)
PRICE = re.compile(r"R\$\s*(\d{1,3}(?:\.\d{3})*|\d+),\d{2}(?!\d)")
QUERY = "geladeira refrigerador side by side 220V Electrolux OR Midea OR LG OR Samsung OR Brastemp preço até R$ 3000 Brasil"

def candidates(results):
    seen = set()
    for item in results:
        url = item.get("url", "")
        title = item.get("title", "")
        snippet = item.get("content", "")
        if urlsplit(url).scheme != "https" or not urlsplit(url).hostname or url in seen:
            continue
        if not all(p.search(title) for p in (BRANDS, MODEL, VOLTAGE)):
            continue
        if re.search(r"\b(usad[ao]|recondicionad[ao]|127\s*v|110\s*v)\b", title, re.I):
            continue
        prices = [float(m.group().replace("R$", "").strip().replace(".", "").replace(",", ".")) for m in PRICE.finditer(title+" "+snippet)]
        prices = [p for p in prices if 500 <= p <= 3000]
        if not prices:
            continue
        seen.add(url)
        yield {"url":url,"title":title,"indicative_price":min(prices),"status":"unverified"}

def reserve(db, now):
    month = now.strftime("%Y-%m")
    hour = now.strftime("%Y-%m-%dT%H")
    db.execute("CREATE TABLE IF NOT EXISTS discovery_calls(hour TEXT PRIMARY KEY, month TEXT)")
    if db.execute("SELECT COUNT(*) FROM discovery_calls WHERE month=?", (month,)).fetchone()[0] >= 744:
        return False
    cur = db.execute("INSERT OR IGNORE INTO discovery_calls VALUES (?,?)",(hour,month))
    db.commit()
    return cur.rowcount == 1

def main():
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        print("Discovery disabled: configure TAVILY_API_KEY.")
        return
    with sqlite3.connect("prices.db") as db:
        if not reserve(db, datetime.now(timezone.utc)):
            return
        response = requests.post("https://api.tavily.com/search", headers={"Authorization":"Bearer "+key}, json={"query":QUERY,"search_depth":"basic","auto_parameters":False,"max_results":20,"include_answer":False,"include_raw_content":False}, timeout=30)
        if not response.ok:
            print("Discovery API HTTP", response.status_code)
            return
        found = list(candidates(response.json().get("results",[])))
        Path("candidates.json").write_text(json.dumps(found,ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
        print("Unverified candidates:",len(found))

if __name__ == "__main__":
    main()
