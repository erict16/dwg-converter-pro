# Product decisions

| Topic | Decision |
|-------|----------|
| GitHub | Public, `erict16/dwg-converter-pro` |
| Glossary in git | Yes (`data/`) |
| MT fallback | MyMemory by default; LibreTranslate if `LIBRETRANSLATE_URL` set |
| Output | Drawing files only (DWG when ODA available, else DXF) |
| UI | Multi-file batch, dark/light theme |
| Disk | Worker `.work` keeps last 8 jobs only |

## Verified

- 2026-07-16: pytest 6 passed
- 2026-07-16: E2E DXF — glossary terms + residual MT (`请确认接线方向` → English)
- Next.js production build OK
