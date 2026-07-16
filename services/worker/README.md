# CAD Worker (scaffold)

Python FastAPI service that will:

1. Accept uploaded `.dwg`
2. Convert via **ODA File Converter** → DXF
3. Extract / replace text with **ezdxf** (TEXT, MTEXT, ATTRIB, MULTILEADER, …)
4. Translate: **glossary longest-match** → **LibreTranslate** fallback
5. Export **DWG only**

## Status

Placeholder only. No convert API yet.

## Planned layout

```
services/worker/
  app/
    main.py          # FastAPI entry
    pipeline.py      # DWG → translate → DWG
    glossary.py      # load data/semantic-glossary.json
    translate.py     # LibreTranslate client
  requirements.txt
  Dockerfile         # optional; Windows host preferred for ODA
```

## Local env (future)

```env
ODA_FC_PATH=C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe
LIBRETRANSLATE_URL=http://localhost:5000
GLOSSARY_PATH=../../data/semantic-glossary.json
```

See root `PLAN.md`.
