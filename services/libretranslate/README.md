# LibreTranslate (self-hosted fallback)

Used **after** project `semantic-glossary` matching for residual Chinese strings.

## Quick start

```bash
docker compose up -d
curl http://localhost:5000/languages
```

## Worker integration (future)

```env
LIBRETRANSLATE_URL=http://localhost:5000
MT_PROVIDER=libre
```

Translate example:

```bash
curl -X POST http://localhost:5000/translate \
  -H "Content-Type: application/json" \
  -d "{\"q\":\"切换开关\",\"source\":\"zh\",\"target\":\"en\"}"
```

Prefer glossary entry `diverter switch` over generic MT when both exist.
