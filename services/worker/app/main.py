"""
CAD Worker API — multi-file Chinese → English drawing translation.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .pipeline import (
    cleanup_old_jobs,
    find_oda,
    new_job_dir,
    process_one_file,
    zip_outputs,
)
from .translate import Translator

app = FastAPI(
    title="DWG Converter Pro Worker",
    version="0.2.0",
    description="Glossary-first ZH→EN for DWG/DXF text entities.",
)

_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILES = int(os.getenv("WORKER_MAX_FILES", "20"))
MAX_MB = int(os.getenv("WORKER_MAX_UPLOAD_MB", "40"))


@app.get("/health")
def health():
    oda = find_oda()
    return {
        "ok": True,
        "service": "dwg-converter-worker",
        "version": "0.2.0",
        "convert": True,
        "oda": bool(oda),
        "oda_path": str(oda) if oda else None,
        "accepts": [".dxf", ".dwg"] if oda else [".dxf"],
        "mt_provider": os.getenv("MT_PROVIDER", "auto"),
    }


@app.post("/v1/convert")
async def convert(files: list[UploadFile] = File(...)):
    if not files:
        return JSONResponse({"ok": False, "error": "no_files"}, status_code=400)
    if len(files) > MAX_FILES:
        return JSONResponse(
            {"ok": False, "error": f"max {MAX_FILES} files per batch"},
            status_code=400,
        )

    cleanup_old_jobs()
    job_dir = new_job_dir()
    uploads = job_dir / "uploads"
    uploads.mkdir()
    results = []
    tr = Translator()

    for uf in files:
        name = uf.filename or "drawing.dxf"
        lower = name.lower()
        if not (lower.endswith(".dwg") or lower.endswith(".dxf")):
            results.append(
                {
                    "original_name": name,
                    "ok": False,
                    "error": "Only .dwg / .dxf accepted",
                }
            )
            continue

        dest = uploads / Path(name).name
        # avoid path traversal
        dest = uploads / dest.name
        content = await uf.read()
        if len(content) > MAX_MB * 1024 * 1024:
            results.append(
                {
                    "original_name": name,
                    "ok": False,
                    "error": f"File exceeds {MAX_MB}MB",
                }
            )
            continue
        dest.write_bytes(content)

        file_work = job_dir / f"f_{dest.stem}"
        file_work.mkdir(exist_ok=True)
        staged = file_work / dest.name
        shutil.copy2(dest, staged)

        # fresh stats per file
        tr_file = Translator(
            glossary=tr.glossary,
            mt_provider=tr.mt_provider,
            libre_url=tr.libre_url,
        )
        r = process_one_file(staged, name, file_work, tr_file)
        results.append(
            {
                "original_name": r.original_name,
                "ok": r.ok,
                "output_name": r.output_name,
                "error": r.error,
                "stats": r.stats,
                "process": r.process,
                "download_path": f"/v1/jobs/{job_dir.name}/files/{r.output_name}"
                if r.ok and r.output_name
                else None,
            }
        )

    ok_results = [r for r in results if r.get("ok") and r.get("output_name")]
    zip_url = None
    if len(ok_results) >= 1:
        # build zip of successes
        from .pipeline import FileJobResult

        fj = []
        for item in results:
            if not item.get("ok"):
                continue
            p = job_dir / f"f_{Path(item['original_name']).stem}" / item["output_name"]
            # output may sit directly under file_work
            if not p.is_file():
                # search
                matches = list((job_dir).rglob(item["output_name"]))
                p = matches[0] if matches else p
            fj.append(
                FileJobResult(
                    original_name=item["original_name"],
                    ok=True,
                    output_name=item["output_name"],
                    output_path=p,
                )
            )
        zip_path = job_dir / "translated.zip"
        zip_outputs(fj, zip_path)
        if zip_path.is_file() and zip_path.stat().st_size > 0:
            zip_url = f"/v1/jobs/{job_dir.name}/zip"

    return {
        "ok": any(r.get("ok") for r in results),
        "job_id": job_dir.name,
        "results": results,
        "zip_url": zip_url,
        "oda": bool(find_oda()),
    }


@app.get("/v1/jobs/{job_id}/zip")
def download_zip(job_id: str):
    job_dir = Path(os.getenv("WORKER_WORK_DIR") or Path(__file__).resolve().parents[1] / ".work") / job_id
    zip_path = job_dir / "translated.zip"
    if not zip_path.is_file():
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    return FileResponse(
        zip_path,
        filename="translated-en.zip",
        media_type="application/zip",
    )


@app.get("/v1/jobs/{job_id}/files/{filename}")
def download_file(job_id: str, filename: str):
    job_dir = Path(os.getenv("WORKER_WORK_DIR") or Path(__file__).resolve().parents[1] / ".work") / job_id
    # prevent path traversal
    safe = Path(filename).name
    matches = list(job_dir.rglob(safe))
    if not matches:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    path = matches[0]
    return FileResponse(path, filename=safe)
