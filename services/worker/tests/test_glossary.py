from pathlib import Path

from app.glossary import Glossary, load_glossary


def test_longest_match_prefers_longer_term():
    g = Glossary(pairs=(("切换开关", "diverter switch"), ("开关", "switch")))
    out, hits = g.apply("主切换开关位置")
    assert "diverter switch" in out
    assert "主" in out
    assert hits >= 1


def test_load_real_glossary():
    g = load_glossary()
    assert len(g.pairs) > 100
    out, hits = g.apply("真空泡和切换开关")
    assert "vacuum interrupter" in out.lower() or "VI" in out
    assert hits >= 1
