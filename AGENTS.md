# DWG Converter Pro — agent notes

## Mission

Chinese DWG/DXF drawings → English **DWG/DXF**. Glossary-first (~393 technical terms), free MT fallback. Multi-file batch. Output drawing files only (no CSV reports required).

## Stack

- `apps/web` — Next.js 15 (Vercel UI): multi-file drop, dark/light theme
- `services/worker` — FastAPI + ezdxf (+ ODA if installed for true DWG)
- `data/semantic-glossary.*` — source of truth for terms

## Translation order

1. Glossary longest-match
2. Residual Chinese → LibreTranslate if `LIBRETRANSLATE_URL` up, else MyMemory
3. Untranslatable left as-is and counted in stats

## Dev

```bash
# worker
cd services/worker
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# web
cd apps/web
npm run dev
# set NEXT_PUBLIC_WORKER_URL=http://127.0.0.1:8000
```

## Tests

```bash
cd services/worker
pytest -q
```

## Space

- Job temps under `services/worker/.work` — auto-cleaned
- Do not commit DWG samples or node_modules / .venv
- Prefer MyMemory over self-hosting Libre models on small disks

## Commits

Commit meaningful milestones with clear messages. Keep public repo clean of secrets.
