from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import httpx

from .glossary import HAS_CJK, Glossary, load_glossary

# MTEXT format codes we keep intact when translating visible segments
_MTEXT_SEGMENT = re.compile(
    r"(\\P|\\p[^;]*;|\\f[^;]*;|\\H[^;]*;|\\W[^;]*;|\\S[^;]*;|\\C\d+;|\\c\d+;|"
    r"\\~|\\{|\\}|\{|\})",
    re.IGNORECASE,
)


@dataclass
class TranslateStats:
    strings_seen: int = 0
    glossary_hits: int = 0
    mt_calls: int = 0
    unchanged: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "strings_seen": self.strings_seen,
            "glossary_hits": self.glossary_hits,
            "mt_calls": self.mt_calls,
            "unchanged": self.unchanged,
            "errors": self.errors[:20],
        }


class Translator:
    def __init__(
        self,
        glossary: Glossary | None = None,
        mt_provider: str | None = None,
        libre_url: str | None = None,
        timeout: float = 20.0,
    ):
        self.glossary = glossary or load_glossary()
        self.mt_provider = (mt_provider or os.getenv("MT_PROVIDER") or "auto").lower()
        self.libre_url = (
            libre_url or os.getenv("LIBRETRANSLATE_URL") or ""
        ).rstrip("/")
        self.timeout = timeout
        self._cache: dict[str, str] = {}
        self.stats = TranslateStats()

    def translate_text(self, text: str) -> str:
        if text is None:
            return text
        if not isinstance(text, str):
            text = str(text)
        if not text.strip() or not HAS_CJK.search(text):
            return text

        self.stats.strings_seen += 1
        if text in self._cache:
            return self._cache[text]

        # 1) glossary
        after_gloss, hits = self.glossary.apply(text)
        self.stats.glossary_hits += hits

        # 2) residual Chinese → MT
        if HAS_CJK.search(after_gloss):
            after_mt = self._mt_fallback(after_gloss)
            if after_mt and after_mt != after_gloss:
                after_gloss = after_mt
            elif HAS_CJK.search(after_gloss):
                self.stats.unchanged += 1

        self._cache[text] = after_gloss
        return after_gloss

    def translate_mtext(self, text: str) -> str:
        """Translate MTEXT while preserving simple format codes."""
        if not text or not HAS_CJK.search(text):
            return text
        # Split on format tokens, translate only plain pieces
        parts = _MTEXT_SEGMENT.split(text)
        out: list[str] = []
        for part in parts:
            if part is None or part == "":
                continue
            if _MTEXT_SEGMENT.fullmatch(part) or part in ("{", "}"):
                out.append(part)
            elif HAS_CJK.search(part):
                out.append(self.translate_text(part))
            else:
                out.append(part)
        return "".join(out)

    def _mt_fallback(self, text: str) -> str:
        provider = self.mt_provider
        if provider == "none":
            return text
        if provider in ("auto", "libre") and self.libre_url:
            try:
                return self._libre(text)
            except Exception as e:  # noqa: BLE001
                self.stats.errors.append(f"libre: {e}")
                if provider == "libre":
                    return text
        if provider in ("auto", "mymemory"):
            try:
                return self._mymemory(text)
            except Exception as e:  # noqa: BLE001
                self.stats.errors.append(f"mymemory: {e}")
        return text

    def _libre(self, text: str) -> str:
        self.stats.mt_calls += 1
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.libre_url}/translate",
                json={"q": text, "source": "zh", "target": "en", "format": "text"},
            )
            r.raise_for_status()
            data = r.json()
            return str(data.get("translatedText") or text)

    def _mymemory(self, text: str) -> str:
        # Free public API — keep strings short
        chunk = text if len(text) <= 450 else text[:450]
        self.stats.mt_calls += 1
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(
                "https://api.mymemory.translated.net/get",
                params={"q": chunk, "langpair": "zh-CN|en"},
            )
            r.raise_for_status()
            data = r.json()
            translated = (
                data.get("responseData", {}).get("translatedText")
                if isinstance(data, dict)
                else None
            )
            if not translated or translated.lower().startswith("query length"):
                return text
            # MyMemory sometimes returns HTML entities / same text
            if translated == chunk:
                return text
            if len(text) > 450:
                return translated + "…"
            return translated
