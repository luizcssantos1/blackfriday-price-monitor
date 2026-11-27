import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

def report(log, outcome, event, failures, now):
    summary = None
    for line in log.splitlines():
        if line.startswith('Search summary: '):
            summary = json.loads(line.split(': ', 1)[1])
    status = 'Falha' if outcome != 'success' else 'Pesquisa não realizada nesta execução'
    if summary is not None and outcome == 'success':
        status = 'Pesquisa realizada'
    lines = ['📊 Black Friday Monitor', now.astimezone(timezone(timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M (Brasília)'), 'Disparo: '+event, 'Descoberta: '+status]
    if summary is not None:
        lines += ['Resultados analisados: '+str(summary['received']), 'Aceitos: '+str(summary['accepted']), 'Rejeitados: '+str(sum(summary['rejected'].values()))]
        lines += [f'{k}: {v}' for k,v in summary['rejected'].items()]
    else:
        lines.append('Contagens indisponíveis nesta execução.')
    if failures:
        lines.append('⚠️ Falhas: '+', '.join(failures))
    lines.append('Orçamento: R$ 5.000 | Side by Side 220 V')
    return '\n'.join(lines)

def main():
    from telegram_notify import notify, send
    now = datetime.now(timezone.utc)
    event = os.getenv('GITHUB_EVENT_NAME', 'unknown')
    outcomes = {k: os.getenv(k, 'unknown') for k in ('TEST_OUTCOME','DISCOVERY_OUTCOME','TELEGRAM_OUTCOME','MONITOR_OUTCOME')}
    failures = [k for k,v in outcomes.items() if v != 'success']
    path = Path('discovery.log')
    message = report(path.read_text() if path.exists() else '', outcomes['DISCOVERY_OUTCOME'], event, failures, now)
    hour = now.strftime('%Y-%m-%dT%H')
    key = 'health:'+hour
    if event == 'workflow_dispatch':
        key = 'manual:'+os.environ['GITHUB_RUN_ID']+':'+os.environ['GITHUB_RUN_ATTEMPT']
    elif failures:
        key = 'error:'+hour+':'+','.join(failures)
    with sqlite3.connect('prices.db') as db:
        print('Health report sent:', notify(db,key,message,send))

if __name__ == '__main__':
    main()
