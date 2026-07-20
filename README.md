# DWG Converter Pro

**Repo:** https://github.com/erict16/dwg-converter-pro

Batch **Chinese → English** for CAD drawing text (DWG/DXF). Technical **glossary first**, free MT fallback. Geometry and leaders stay; only strings change.

## Features

- Multi-file drag & drop queue + batch convert + ZIP download
- Dark / light theme
- Glossary (~393 terms) longest-match
- MyMemory (or LibreTranslate if configured) for residual Chinese
- TEXT / MTEXT / ATTRIB / MULTILEADER / DIMENSION overrides / block contents
- Worker job temps auto-pruned (low disk footprint)

## Quick start (local)

### 1) Worker

```powershell
cd C:\repo\dwg-converter-pro\services\worker
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Or: `scripts\dev-worker.ps1`

Health: http://127.0.0.1:8000/health

### 2) Web

```powershell
cd C:\repo\dwg-converter-pro\apps\web
copy .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

### DWG in / DWG out (product promise)

**Users only upload and download `.dwg`.** No “please convert to DXF” in the UI.

Internally the Windows worker may use [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter) **silently** (DWG→edit→DWG). Install ODA once on the **worker machine** and optionally set `ODA_FC_PATH`.

| What user sees | What worker does |
|----------------|------------------|
| Upload `.dwg` | Silent convert if needed |
| Download `*-EN.dwg` | Silent export back to DWG |

DXF is still accepted for testing without ODA.

## Tests

```powershell
cd services\worker
.\.venv\Scripts\python -m pytest -q
```

## Vercel

1. Import GitHub repo  
2. Root Directory: `apps/web`  
3. Set `NEXT_PUBLIC_WORKER_URL` to your deployed/public worker URL  

The CAD worker cannot run on Vercel serverless (needs filesystem + optional ODA).

## Layout

```
apps/web/                 Next.js UI (Vercel)
services/worker/          FastAPI + ezdxf pipeline
services/libretranslate/  optional self-host MT
data/                     semantic-glossary.xlsx/json
```

## Env

Worker:

```env
MT_PROVIDER=auto          # auto | mymemory | libre | none
LIBRETRANSLATE_URL=       # optional
ODA_FC_PATH=              # optional path to ODAFileConverter.exe
WORKER_MAX_FILES=20
WORKER_MAX_UPLOAD_MB=40
```

Web:

```env
NEXT_PUBLIC_WORKER_URL=http://127.0.0.1:8000
```

## License

Public scaffold; treat the technical glossary as internal terminology — use responsibly.
