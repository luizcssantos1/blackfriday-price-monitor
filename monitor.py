import os, json, re, sqlite3
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

LIMIT = 3000
BRANDS = ("Electrolux", "Midea", "LG", "Samsung", "Brastemp")
BRAND_PATTERN = re.compile(r"\b(?:" + "|".join(map(re.escape, BRANDS)) + r")\b", re.I)

def allowed_brand(product):
    brand = product.get("brand")
    if isinstance(brand, dict):
        brand = brand.get("name")
    if isinstance(brand, str) and brand.strip():
        return brand.strip().casefold() in {b.casefold() for b in BRANDS}
    return bool(BRAND_PATTERN.search(str(product.get("name", ""))))

DB = sqlite3.connect('prices.db')
DB.execute('CREATE TABLE IF NOT EXISTS prices(url TEXT, date TEXT, price REAL)')
DB.execute('CREATE TABLE IF NOT EXISTS alerts(url TEXT, price REAL, PRIMARY KEY(url,price))')
DB.commit()

def products(obj):
    if isinstance(obj, list):
        for item in obj: yield from products(item)
    elif isinstance(obj, dict):
        if 'Product' in ([obj.get('@type')] if isinstance(obj.get('@type'),str) else obj.get('@type',[])): yield obj
        for value in obj.values():
            if isinstance(value,(dict,list)): yield from products(value)

def check(url):
    r=requests.get(url,timeout=25,headers={'User-Agent':'PriceMonitor/1.0'}); r.raise_for_status()
    soup=BeautifulSoup(r.text,'html.parser')
    for tag in soup.select('script[type="application/ld+json"]'):
        try: data=json.loads(tag.get_text())
        except ValueError: continue
        for p in products(data):
            name=p.get('name','')
            if not allowed_brand(p): continue
            if not re.search(r'side[ -]by[ -]side',name,re.I): continue
            if not re.search(r'\b220\s*v\b',name,re.I): continue
            offers=p.get('offers',[])
            for offer in offers if isinstance(offers,list) else [offers]:
                if offer.get('priceCurrency')!='BRL' or not str(offer.get('availability','')).endswith('/InStock'): continue
                if str(offer.get('itemCondition','')).endswith(('UsedCondition','RefurbishedCondition')): continue
                try: price=float(offer['price'])
                except (KeyError,ValueError,TypeError): continue
                if price<=0: continue
                previous=DB.execute('SELECT MIN(price) FROM prices WHERE url=?',(url,)).fetchone()[0]
                DB.execute('INSERT INTO prices VALUES(?,?,?)',(url,datetime.now(timezone.utc).isoformat(),price)); DB.commit()
                if price>LIMIT or DB.execute('SELECT 1 FROM alerts WHERE url=? AND price=?',(url,price)).fetchone(): continue
                msg=f'{name}\nR$ {price:.2f}\nMenor preço observado antes: {previous if previous is not None else "sem histórico"}\nFrete e condição nova: confirmar na loja.\n{url}'
                print(msg)
                token=os.environ.get('TELEGRAM_BOT_TOKEN'); chat=os.environ.get('TELEGRAM_CHAT_ID')
                if token and chat:
                    resp=requests.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':msg},timeout=20); resp.raise_for_status()
                    DB.execute('INSERT OR IGNORE INTO alerts VALUES(?,?)',(url,price)); DB.commit()

urls=json.loads(Path('urls.json').read_text())
if not urls: print('Adicione URLs de produtos 220 V em urls.json.')
for url in urls:
    try: check(url)
    except Exception as e: print(f'Falha na consulta: {url} ({type(e).__name__})')
DB.close()
