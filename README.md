
# Portal de Vagas e QRs — Viação Reunidas (Flask)

## Rodar local
```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
# http://localhost:8000
```

## Rotas principais
- `/vagas` — lista de vagas.
- `/vaga/<slug>` — detalhe + formulário com upload (salva em `uploads/` e em `applications` no SQLite).
- `/?bus=045` — adiciona parâmetro do ônibus para analytics.
- `/r/<slug>` — redireciona e rastreia cliques dos botões do índice.
- `/qr/<slug>.png?bus=045` — gera QR de qualquer botão.
- `/admin?k=TOKEN` — painel simples (defina `ADMIN_TOKEN` no ambiente).
- `/export.csv?k=TOKEN` e `/candidatos.csv?k=TOKEN` — exportações.

## Como editar
- Abra `config.json` para mudar texto, vagas e links.
- Os QRs para divulgação de vagas podem apontar para `/vagas?bus=XXX`.

## Produção (resumo)
Use Gunicorn + Nginx ou IIS (via wfastcgi) conforme seu ambiente.
