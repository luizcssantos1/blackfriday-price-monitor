import re
from urllib.parse import urlsplit

OTHER = re.compile(r'\b(Consul|Philco|Panasonic|Hisense|Bosch|TCL|EOS|Britânia)\b', re.I)

def catalog(url):
    p = urlsplit(url)
    return bool(re.search(r'/(s|search|busca|pesquisa|categoria|categorias)(/|$)', p.path, re.I) or re.search(r'(?:^|&)(?:q|query|search|page)=', p.query, re.I))

def review_reason(url, text, reason):
    if reason == 'brand_missing' and OTHER.search(text):
        return 'other_brand'
    return reason or ('catalog_page' if catalog(url) else None)

def record(url, title, text, reason, price_pattern, voltage_pattern):
    return dict(url=url, title=title, reason=reason, catalog=catalog(url), prices=list(dict.fromkeys(m.group() for m in price_pattern.finditer(text))), voltage='220 V' if voltage_pattern.search(text) else 'Não confirmada')

def message(item):
    return '\n'.join(['🔎 Análise manual — '+item['reason'], item['title'][:500], 'Catálogo (não é produto individual)' if item['catalog'] else 'Página não verificada', 'Valores citados (não confirmados): '+(', '.join(item['prices'])[:500] or 'Não informado'), 'Voltagem: '+item['voltage'], item['url']])
