from pathlib import Path

import ezdxf

from app.dxf_text import process_drawing
from app.translate import Translator
from app.pipeline import process_one_file


def _make_sample_dxf(path: Path) -> None:
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_text("切换开关", dxfattribs={"height": 2.5, "insert": (0, 0)})
    msp.add_text("真空泡", dxfattribs={"height": 2.5, "insert": (0, 10)})
    msp.add_mtext("限位开关\\P机械端位止动装置", dxfattribs={"insert": (20, 0), "char_height": 2})
    # non-chinese should stay
    msp.add_text("SHZV-12233W", dxfattribs={"height": 2.5, "insert": (0, 20)})
    doc.saveas(path)


def test_process_drawing_translates_glossary_terms(tmp_path: Path):
    src = tmp_path / "cn.dxf"
    _make_sample_dxf(src)
    doc = ezdxf.readfile(src)
    tr = Translator(mt_provider="none")
    result = process_drawing(doc, tr)
    assert result.chinese_found >= 3
    assert result.entities_touched >= 3

    texts = []
    for e in doc.modelspace():
        if e.dxftype() == "TEXT":
            texts.append(e.dxf.text)
        if e.dxftype() == "MTEXT":
            texts.append(e.text)
    blob = "\n".join(texts)
    assert "切换开关" not in blob
    assert "真空泡" not in blob
    assert "diverter switch" in blob.lower() or "Diverter" in blob
    assert "SHZV-12233W" in blob


def test_process_one_file_dxf(tmp_path: Path):
    src = tmp_path / "sample-cn.dxf"
    _make_sample_dxf(src)
    work = tmp_path / "work"
    work.mkdir()
    tr = Translator(mt_provider="none")
    r = process_one_file(src, "sample-cn.dxf", work, tr)
    assert r.ok, r.error
    assert r.output_path and r.output_path.is_file()
    assert r.output_name.endswith(".dxf")
    content = r.output_path.read_text(encoding="utf-8", errors="ignore")
    assert "切换开关" not in content
    assert "diverter" in content.lower() or "switch" in content.lower()
