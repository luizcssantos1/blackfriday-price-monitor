import os
import json
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from decimal import Decimal
import requests
from review import catalog, message as review_message

def canonical(url):
    p = urlsplit(url)
    query = urlencode(sorted((k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith("utm_") and k.lower() not in ("gclid","fbclid")))
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip("/"),query,""))

def notify(db, key, message, sender):
    db.execute("CREATE TABLE IF NOT EXISTS telegram_notifications (key TEXT PRIMARY KEY)")
    if db.execute("SELECT 1 FROM telegram_notifications WHERE key=?", (key,)).fetchone():
        return False
    sender(message)
    db.execute("INSERT INTO telegram_notifications VALUES (?)",(key,))
    db.commit()
    return True

def send(message):
    token=os.environ["TELEGRAM_BOT_TOKEN"]
    chat=os.environ["TELEGRAM_CHAT_ID"]
    try:
        response=requests.post("https://api.telegram.org/bot"+token+"/sendMessage",json={"chat_id":chat,"text":message,"link_preview_options":{"is_disabled":True}},timeout=20)
        if not response.ok or not response.json().get("ok"):
            raise RuntimeError("Telegram rejected message (HTTP "+str(response.status_code)+")")
    except requests.RequestException:
        raise RuntimeError("Telegram network error") from None

def main():
    if not all(os.getenv(k) for k in ("TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID")):
        raise SystemExit("Telegram secrets missing")
    with sqlite3.connect("prices.db") as db:
        if notify(db,"setup-test-v1","✅ Black Friday Monitor: integração Telegram ativa! Side by Side 220 V até R$ 5.000. Brasília – DF.",send):
            print("Telegram test sent")
        path=Path("candidates.json")
        items=json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        count=0
        for item in items:
            price=Decimal(str(item["indicative_price"]))
            if not price.is_finite() or not 0 < price <= 5000:
                continue
            url=item["url"]
            if urlsplit(url).scheme!="https" or catalog(url):
                continue
            key="candidate:"+canonical(url)+":"+str(price.quantize(Decimal("0.01")))
            value=f"{price:,.2f}".replace(",","X").replace(".",",").replace("X",".")
            message=f"🧊 Oferta candidata (não verificada)\n{item['title'][:500]}\nPreço indicativo: R$ {value}\nConfirme 220 V, condição nova, estoque, total parcelado e frete para Brasília.\n{url}"
            count+=notify(db,key,message,send)
        print("New candidate notifications:",count)
        rejected = Path("rejected.json")
        if rejected.exists():
            for item in json.loads(rejected.read_text(encoding="utf-8")):
                if item["reason"] not in ("brand_missing","other_brand","catalog_page"):
                    continue
                url = item["url"]
                if urlsplit(url).scheme != "https":
                    continue
                key = "review:"+canonical(url)+":"+item["reason"]+":"+",".join(sorted(item["prices"]))+":"+item["voltage"]
                notify(db,key,review_message(item),send)

if __name__=="__main__":
    main()
