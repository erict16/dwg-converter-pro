from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .dxf_text import process_drawing, load_dxf, save_dxf
from .translate import Translator

WORK_ROOT = Path(os.getenv("WORKER_WORK_DIR") or Path(__file__).resolve().parents[1] / ".work")


@dataclass
class FileJobResult:
    original_name: str
    ok: bool
    output_name: str | None = None
    output_path: Path | None = None
    error: str | None = None
    stats: dict = field(default_factory=dict)
    process: dict = field(default_factory=dict)


def find_oda() -> Path | None:
    env = os.getenv("ODA_FC_PATH")
    if env and Path(env).is_file():
        return Path(env)
    candidates = [
        Path(r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"),
        Path(r"C:\Program Files\ODA\ODAFileConverter 26.4.0\ODAFileConverter.exe"),
        Path(r"C:\Program Files\ODA\ODAFileConverter 25.12.0\ODAFileConverter.exe"),
        Path(r"C:\Program Files\ODA\ODAFileConverter 25.4.0\ODAFileConverter.exe"),
        Path(r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    # search shallow under Program Files\ODA
    root = Path(r"C:\Program Files\ODA")
    if root.is_dir():
        for p in root.rglob("ODAFileConverter.exe"):
            return p
    return None


def oda_convert(oda: Path, src_dir: Path, dst_dir: Path, out_version: str, out_type: str) -> None:
    """
    ODAFileConverter input_folder output_folder output_version output_filetype recurse audit
    out_type: "DWG" or "DXF"
    out_version e.g. "ACAD2018"
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(oda),
        str(src_dir),
        str(dst_dir),
        out_version,
        out_type,
        "0",  # recurse off
        "1",  # audit on
    ]
    # ODA is a GUI app that can exit before finishing on some versions — run and wait
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if proc.returncode not in (0, None):
        # many ODA builds return 0 always; check output exists later
        pass


def _out_stem(name: str) -> str:
    p = Path(name)
    return f"{p.stem}-EN{p.suffix.lower()}"


def process_one_file(
    src: Path,
    original_name: str,
    work_dir: Path,
    translator: Translator | None = None,
) -> FileJobResult:
    tr = translator or Translator()
    tr.stats = type(tr.stats)()  # reset per file if shared? keep cumulative if same instance
    suffix = src.suffix.lower()
    oda = find_oda()

    try:
        if suffix == ".dxf":
            doc = load_dxf(src)
            proc = process_drawing(doc, tr)
            out_name = _out_stem(original_name)
            if not out_name.lower().endswith(".dxf"):
                out_name = Path(original_name).stem + "-EN.dxf"
            out_path = work_dir / out_name
            save_dxf(doc, out_path)
            return FileJobResult(
                original_name=original_name,
                ok=True,
                output_name=out_name,
                output_path=out_path,
                stats=tr.stats.as_dict(),
                process=proc.as_dict(),
            )

        if suffix == ".dwg":
            if not oda:
                return FileJobResult(
                    original_name=original_name,
                    ok=False,
                    error=(
                        "Server CAD engine is not ready for DWG yet "
                        "(missing ODA File Converter on the worker machine). "
                        "Please try again later — you do not need to convert the file yourself."
                    ),
                )
            in_dir = work_dir / "oda_in"
            dxf_dir = work_dir / "oda_dxf"
            out_dir = work_dir / "oda_out"
            in_dir.mkdir(parents=True, exist_ok=True)
            # ODA expects files in folder
            staged = in_dir / src.name
            if staged.resolve() != src.resolve():
                shutil.copy2(src, staged)

            oda_convert(oda, in_dir, dxf_dir, "ACAD2018", "DXF")
            # find produced dxf
            dxfs = list(dxf_dir.glob("*.dxf")) + list(dxf_dir.glob("*.DXF"))
            if not dxfs:
                # try same stem
                cand = dxf_dir / (src.stem + ".dxf")
                if not cand.exists():
                    return FileJobResult(
                        original_name=original_name,
                        ok=False,
                        error="Could not process this DWG (CAD engine failed). Try another version or contact support — no manual format conversion needed.",
                    )
                dxfs = [cand]
            dxf_path = dxfs[0]
            doc = load_dxf(dxf_path)
            proc = process_drawing(doc, tr)
            # save intermediate translated dxf
            en_dxf_dir = work_dir / "en_dxf"
            en_dxf_dir.mkdir(exist_ok=True)
            en_dxf = en_dxf_dir / (src.stem + "-EN.dxf")
            save_dxf(doc, en_dxf)

            oda_convert(oda, en_dxf_dir, out_dir, "ACAD2018", "DWG")
            dwgs = list(out_dir.glob("*.dwg")) + list(out_dir.glob("*.DWG"))
            if not dwgs:
                # fallback: return DXF if DWG export failed
                out_name = src.stem + "-EN.dxf"
                final = work_dir / out_name
                shutil.copy2(en_dxf, final)
                return FileJobResult(
                    original_name=original_name,
                    ok=True,
                    output_name=out_name,
                    output_path=final,
                    stats=tr.stats.as_dict(),
                    process={**proc.as_dict(), "note": "Returned DXF; ODA DWG export missing"},
                )
            out_name = src.stem + "-EN.dwg"
            final = work_dir / out_name
            shutil.copy2(dwgs[0], final)
            return FileJobResult(
                original_name=original_name,
                ok=True,
                output_name=out_name,
                output_path=final,
                stats=tr.stats.as_dict(),
                process=proc.as_dict(),
            )

        return FileJobResult(
            original_name=original_name,
            ok=False,
            error=f"Unsupported type: {suffix}",
        )
    except Exception as e:  # noqa: BLE001
        return FileJobResult(original_name=original_name, ok=False, error=str(e))


def new_job_dir() -> Path:
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    d = WORK_ROOT / uuid.uuid4().hex
    d.mkdir(parents=True, exist_ok=True)
    return d


def zip_outputs(results: list[FileJobResult], zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for r in results:
            if r.ok and r.output_path and r.output_path.is_file():
                zf.write(r.output_path, arcname=r.output_name or r.output_path.name)
    return zip_path


def cleanup_old_jobs(max_keep: int = 8) -> None:
    """Limit disk use: keep only newest job folders."""
    if not WORK_ROOT.is_dir():
        return
    jobs = sorted(
        [p for p in WORK_ROOT.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in jobs[max_keep:]:
        shutil.rmtree(old, ignore_errors=True)
