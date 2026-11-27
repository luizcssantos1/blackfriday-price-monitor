# Black Friday Price Monitor

Python + GitHub Actions + SQLite + Telegram.

## Português
Monitora páginas de produtos cadastradas em `urls.json` (lista JSON de URLs autorizadas para consulta automatizada). Filtros: Side by Side, 220 V, até R$ 3.000 sem frete, Electrolux, Midea, LG, Samsung e Brastemp. Exige JSON-LD compatível e estoque informado. Confirme condição, vendedor e frete para Brasília antes da compra. Não descobre novos produtos automaticamente. O histórico começa na primeira execução.

Em Settings > Secrets and variables > Actions, configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID após criar um bot no BotFather e iniciar conversa com ele. Não publique credenciais. Em Actions > Monitor de geladeiras > Run workflow, execute manualmente. O cron roda aproximadamente a cada 30 minutos, sujeito a atrasos. O workflow precisa de permissão de escrita para persistir prices.db. Desative após a compra.

## English
Tracks registered product URLs with compatible JSON-LD and explicit 220 V, Side by Side, in-stock offers up to BRL 3,000 before shipping. Allowed brands: Electrolux, Midea, LG, Samsung and Brastemp. Product discovery is not implemented. Verify condition, seller and shipping before purchasing.

Add authorized product URLs to urls.json. Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as repository Actions secrets. Run the workflow manually or use its approximate 30-minute schedule. Repository write permission is required to persist SQLite history.

## Local
```sh
pip install -r requirements.txt
python monitor.py
```
