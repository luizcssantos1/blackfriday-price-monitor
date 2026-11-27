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
QUERIES = ["geladeira side by side 220V preço total até 5000 parcelado cartão Brasil"] + [
    "geladeira side by side 220V preço total parcelado " + brand
    for brand in ("Electrolux", "Midea", "LG", "Samsung", "Brastemp")
] + [
    "geladeira side by side 220V oferta " + store
    for store in ("Magalu", "Casas Bahia", "Fast Shop", "Carrefour", "Amazon Brasil")
]

def query_for(now):
    return QUERIES[int(now.timestamp() // 3600) % len(QUERIES)]

def candidates(results):
    from collections import Counter
    reasons = Counter()
    seen = set()
    for item in results:
        url = item.get("url", "")
        title = item.get("title", "")
        snippet = item.get("content", "")
        combined = title + " " + snippet
        reason = None
        if urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
            reason = "invalid_url"
        elif url in seen:
            reason = "duplicate"
        elif not BRANDS.search(combined):
            reason = "brand_missing"
        elif not MODEL.search(combined):
            reason = "model_missing"
        elif not VOLTAGE.search(combined):
            reason = "voltage_missing"
        elif re.search(r"\b(usad[ao]|recondicionad[ao]|127\s*v|110\s*v)\b", combined, re.I):
            reason = "condition_or_voltage_conflict"
        else:
            prices = []
            for m in PRICE.finditer(combined):
                before = combined[max(0,m.start()-35):m.start()]
                after = combined[m.end():m.end()+35]
                if re.search(r"\d+\s*x\s*(?:de\s*)?$|parcela[s]?\s*(?:de\s*)?$", before, re.I) or re.search(r"^\s*(?:/mês|por mês|cada parcela)", after, re.I):
                    continue
                prices.append(float(m.group().replace("R$", "").strip().replace(".", "").replace(",", ".")))
            if not prices:
                reason = "no_non_installment_price"
            elif not all(500 <= p <= 5000 for p in prices):
                reason = "price_outside_range_or_ambiguous"
        if reason:
            reasons[reason] += 1
            print("Rejected:", reason, url)
            continue
        seen.add(url)
        yield {"url":url,"title":title,"indicative_price":min(prices),"status":"unverified"}
    print("Search summary:", json.dumps({"received":len(results),"accepted":len(seen),"rejected":dict(reasons)}))

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
        now = datetime.now(timezone.utc)
        if not reserve(db, now):
            print("Discovery skipped: hourly or monthly quota reached.")
            return
        query = query_for(now)
        print("Search query:", query)
        print("Monthly reserved calls:", db.execute("SELECT COUNT(*) FROM discovery_calls WHERE month=?", (now.strftime("%Y-%m"),)).fetchone()[0])
        response = requests.post("https://api.tavily.com/search", headers={"Authorization":"Bearer "+key}, json={"query":query,"search_depth":"basic","auto_parameters":False,"max_results":20,"include_answer":False,"include_raw_content":False}, timeout=30)
        if not response.ok:
            print("Discovery API HTTP", response.status_code)
            raise SystemExit(1)
        found = list(candidates(response.json().get("results",[])))
        Path("candidates.json").write_text(json.dumps(found,ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
        print("Unverified candidates:",len(found))

if __name__ == "__main__":
    main()
