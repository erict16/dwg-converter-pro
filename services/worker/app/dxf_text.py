from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import ezdxf
from ezdxf.document import Drawing
from ezdxf.entities import DXFEntity

from .glossary import HAS_CJK
from .translate import Translator


@dataclass
class EntityChange:
    handle: str
    dxftype: str
    before: str
    after: str


@dataclass
class ProcessResult:
    changes: list[EntityChange] = field(default_factory=list)
    entities_touched: int = 0
    chinese_found: int = 0

    def as_dict(self) -> dict:
        return {
            "entities_touched": self.entities_touched,
            "chinese_found": self.chinese_found,
            "change_count": len(self.changes),
            "sample_changes": [
                {
                    "handle": c.handle,
                    "type": c.dxftype,
                    "before": c.before[:120],
                    "after": c.after[:120],
                }
                for c in self.changes[:30]
            ],
        }


def _handle(e: DXFEntity) -> str:
    try:
        return str(e.dxf.handle)
    except Exception:  # noqa: BLE001
        return "?"


def _set_if_changed(
    result: ProcessResult,
    entity: DXFEntity,
    before: str,
    after: str,
    apply,
) -> None:
    if before is None:
        return
    before_s = str(before)
    if not HAS_CJK.search(before_s):
        return
    result.chinese_found += 1
    if after == before_s:
        return
    apply(after)
    result.entities_touched += 1
    result.changes.append(
        EntityChange(
            handle=_handle(entity),
            dxftype=entity.dxftype(),
            before=before_s,
            after=after,
        )
    )


def _process_entity(entity: DXFEntity, tr: Translator, result: ProcessResult) -> None:
    t = entity.dxftype()

    if t == "TEXT":
        raw = entity.dxf.text
        _set_if_changed(
            result, entity, raw, tr.translate_text(raw), lambda v: setattr(entity.dxf, "text", v)
        )
        return

    if t == "MTEXT":
        raw = entity.text

        def _apply_mtext(v: str) -> None:
            try:
                entity.text = v
            except Exception:  # noqa: BLE001
                if hasattr(entity, "set_text"):
                    entity.set_text(v)

        _set_if_changed(result, entity, raw, tr.translate_mtext(str(raw or "")), _apply_mtext)
        return

    if t in ("ATTRIB", "ATTDEF"):
        raw = entity.dxf.text
        _set_if_changed(
            result, entity, raw, tr.translate_text(raw), lambda v: setattr(entity.dxf, "text", v)
        )
        return

    if t == "MULTILEADER":
        _process_multileader(entity, tr, result)
        return

    if t == "DIMENSION":
        # Override text if present (not "<>")
        try:
            raw = entity.dxf.get("text", "") or ""
        except Exception:  # noqa: BLE001
            raw = ""
        if raw and raw != "<>" and HAS_CJK.search(str(raw)):
            _set_if_changed(
                result,
                entity,
                raw,
                tr.translate_text(str(raw)),
                lambda v: setattr(entity.dxf, "text", v),
            )
        return


def _process_multileader(entity: Any, tr: Translator, result: ProcessResult) -> None:
    """Best-effort MULTILEADER / MLeader text."""
    # ezdxf MLeader context structure varies by version
    try:
        ctx = entity.context
    except Exception:  # noqa: BLE001
        ctx = None

    if ctx is not None:
        # mtext content
        for attr in ("mtext", "default_content", "content"):
            if hasattr(ctx, attr):
                try:
                    m = getattr(ctx, attr)
                    if m is None:
                        continue
                    if hasattr(m, "default_content"):
                        raw = m.default_content
                        new = tr.translate_mtext(str(raw or ""))
                        if raw and new != raw and HAS_CJK.search(str(raw)):
                            m.default_content = new
                            result.chinese_found += 1
                            result.entities_touched += 1
                            result.changes.append(
                                EntityChange(_handle(entity), "MULTILEADER", str(raw), new)
                            )
                    elif isinstance(m, str) and HAS_CJK.search(m):
                        new = tr.translate_mtext(m)
                        if new != m:
                            setattr(ctx, attr, new)
                            result.chinese_found += 1
                            result.entities_touched += 1
                            result.changes.append(
                                EntityChange(_handle(entity), "MULTILEADER", m, new)
                            )
                except Exception:  # noqa: BLE001
                    continue

    # Some versions store content on dxf export via virtual entities — also try DXF tags
    try:
        if hasattr(entity, "get_mtext_content"):
            raw = entity.get_mtext_content()
            if raw and HAS_CJK.search(str(raw)):
                new = tr.translate_mtext(str(raw))
                if new != raw and hasattr(entity, "set_mtext_content"):
                    entity.set_mtext_content(new)
                    result.chinese_found += 1
                    result.entities_touched += 1
                    result.changes.append(
                        EntityChange(_handle(entity), "MULTILEADER", str(raw), new)
                    )
    except Exception:  # noqa: BLE001
        pass


def process_drawing(doc: Drawing, tr: Translator | None = None) -> ProcessResult:
    tr = tr or Translator()
    result = ProcessResult()

    # Modelspace + paperspace layouts
    for layout in doc.layouts:
        for entity in layout:
            try:
                _process_entity(entity, tr, result)
            except Exception:  # noqa: BLE001
                continue
            # ATTRIB on INSERT
            if entity.dxftype() == "INSERT":
                try:
                    for attrib in entity.attribs:
                        _process_entity(attrib, tr, result)
                except Exception:  # noqa: BLE001
                    pass

    # Block definitions (except *Model_Space etc. already covered via layouts)
    for block in doc.blocks:
        name = block.name
        if name.startswith("*"):
            # still process anonymous dimension blocks carefully — skip pure layout blocks
            if name.upper() in ("*MODEL_SPACE", "*PAPER_SPACE") or name.upper().startswith(
                "*PAPER_SPACE"
            ):
                continue
        for entity in block:
            try:
                _process_entity(entity, tr, result)
            except Exception:  # noqa: BLE001
                continue

    return result


def load_dxf(path) -> Drawing:
    return ezdxf.readfile(str(path))


def save_dxf(doc: Drawing, path) -> None:
    doc.saveas(str(path))
