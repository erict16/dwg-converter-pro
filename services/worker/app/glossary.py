from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

HAS_CJK = re.compile(r"[\u4e00-\u9fff]")


@dataclass(frozen=True)
class Glossary:
    """Longest-match Chinese → English glossary."""

    pairs: tuple[tuple[str, str], ...]  # sorted by zh length desc

    @classmethod
    def from_json(cls, path: Path) -> "Glossary":
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get("entries") or []
        pairs = []
        for e in entries:
            zh = str(e.get("zh") or "").strip()
            en = str(e.get("en") or "").strip()
            if zh and en:
                pairs.append((zh, en))
        # longest first so "切换开关" wins over "开关"
        pairs.sort(key=lambda p: len(p[0]), reverse=True)
        return cls(pairs=tuple(pairs))

    def apply(self, text: str) -> tuple[str, int]:
        """Replace glossary terms. Returns (new_text, hit_count)."""
        if not text or not HAS_CJK.search(text):
            return text, 0
        out = text
        hits = 0
        for zh, en in self.pairs:
            if zh in out:
                n = out.count(zh)
                out = out.replace(zh, en)
                hits += n
        return out, hits


def default_glossary_path() -> Path:
    # services/worker/app/glossary.py → repo/data/semantic-glossary.json
    return Path(__file__).resolve().parents[3] / "data" / "semantic-glossary.json"


@lru_cache(maxsize=1)
def load_glossary(path: str | None = None) -> Glossary:
    p = Path(path) if path else default_glossary_path()
    return Glossary.from_json(p)
