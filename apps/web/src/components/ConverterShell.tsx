"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  absoluteWorkerUrl,
  convertFiles,
  fetchHealth,
  type ConvertFileResult,
} from "@/lib/worker";

type QueueItem = {
  id: string;
  file: File;
  name: string;
  size: number;
  status: "queued" | "running" | "ok" | "error";
  message?: string;
  downloadUrl?: string;
  statsLabel?: string;
};

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function uid(file: File) {
  return `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2, 7)}`;
}

export function ConverterShell() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [zipUrl, setZipUrl] = useState<string | null>(null);
  const [workerOk, setWorkerOk] = useState<boolean | null>(null);
  const [oda, setOda] = useState(false);
  const [message, setMessage] = useState(
    "Add Chinese .dwg / .dxf files, then convert the whole queue in one go."
  );

  const refreshHealth = useCallback(async () => {
    try {
      const h = await fetchHealth();
      setWorkerOk(!!h.ok);
      setOda(!!h.oda);
      if (!h.oda) {
        setMessage(
          "Worker online. ODA not detected — DXF works fully; install ODA File Converter for native DWG."
        );
      } else {
        setMessage("Worker online with ODA — DWG and DXF ready.");
      }
    } catch {
      setWorkerOk(false);
      setMessage(
        "Worker offline. Start it: cd services/worker && .venv\\Scripts\\uvicorn app.main:app --port 8000"
      );
    }
  }, []);

  useEffect(() => {
    refreshHealth();
    const t = setInterval(refreshHealth, 15000);
    return () => clearInterval(t);
  }, [refreshHealth]);

  const acceptFiles = useCallback((list: FileList | File[]) => {
    const next: QueueItem[] = [];
    let skipped = 0;
    for (const file of Array.from(list)) {
      const lower = file.name.toLowerCase();
      if (!lower.endsWith(".dwg") && !lower.endsWith(".dxf")) {
        skipped += 1;
        continue;
      }
      next.push({
        id: uid(file),
        file,
        name: file.name,
        size: file.size,
        status: "queued",
      });
    }
    if (next.length) {
      setItems((prev) => {
        const names = new Set(prev.map((p) => `${p.name}:${p.size}`));
        const merged = [...prev];
        for (const n of next) {
          const key = `${n.name}:${n.size}`;
          if (!names.has(key)) merged.push(n);
        }
        return merged;
      });
      setZipUrl(null);
      setMessage(
        `Queued ${next.length} file(s)${skipped ? ` · skipped ${skipped} non-CAD` : ""}.`
      );
    } else if (skipped) {
      setMessage("Only .dwg and .dxf files are accepted.");
    }
  }, []);

  const removeItem = (id: string) => {
    setItems((prev) => prev.filter((x) => x.id !== id));
    setZipUrl(null);
  };

  const canConvert = useMemo(
    () => items.length > 0 && !busy && workerOk !== false,
    [items.length, busy, workerOk]
  );

  const progress = useMemo(() => {
    if (!items.length) return 0;
    const done = items.filter((i) => i.status === "ok" || i.status === "error").length;
    if (busy && done === 0) return 12;
    return Math.round((done / items.length) * 100);
  }, [items, busy]);

  const onConvert = async () => {
    if (!items.length || busy) return;
    setBusy(true);
    setZipUrl(null);
    setItems((prev) =>
      prev.map((i) => ({ ...i, status: "running" as const, message: "Uploading…" }))
    );
    setMessage("Converting batch… glossary first, then MT for leftovers.");

    try {
      const res = await convertFiles(items.map((i) => i.file));
      const byName = new Map<string, ConvertFileResult>();
      for (const r of res.results) byName.set(r.original_name, r);

      setItems((prev) =>
        prev.map((item) => {
          const r = byName.get(item.name);
          if (!r) {
            return { ...item, status: "error", message: "No result from worker" };
          }
          if (!r.ok) {
            return {
              ...item,
              status: "error",
              message: r.error || "Failed",
            };
          }
          const hits = r.stats?.glossary_hits ?? 0;
          const touched = r.process?.entities_touched ?? r.process?.change_count ?? 0;
          return {
            ...item,
            status: "ok",
            message: r.output_name || "done",
            downloadUrl: r.download_path
              ? absoluteWorkerUrl(r.download_path)
              : undefined,
            statsLabel: `${touched} text · ${hits} glossary`,
          };
        })
      );

      if (res.zip_url) {
        setZipUrl(absoluteWorkerUrl(res.zip_url));
      }
      const okCount = res.results.filter((r) => r.ok).length;
      const failCount = res.results.length - okCount;
      setMessage(
        `Done: ${okCount} ok${failCount ? `, ${failCount} failed` : ""}.` +
          (res.oda === false
            ? " Tip: install ODA for DWG round-trip; DXF is fully supported."
            : "")
      );
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setItems((prev) =>
        prev.map((i) => ({ ...i, status: "error", message: msg }))
      );
      setMessage(`Convert failed: ${msg}`);
      setWorkerOk(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {workerOk === false && (
        <div className="banner">
          Worker not reachable at{" "}
          <code>{process.env.NEXT_PUBLIC_WORKER_URL || "http://127.0.0.1:8000"}</code>
          . Start the Python service to convert files.
        </div>
      )}

      <div className="panel">
        <label
          className={`dropzone${dragOver ? " dragover" : ""}`}
          onDragEnter={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            setDragOver(false);
          }}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (e.dataTransfer.files?.length) acceptFiles(e.dataTransfer.files);
          }}
        >
          <div>
            <h2>Drop Chinese drawings here</h2>
            <p>Multiple .dwg / .dxf — queue them all, convert once</p>
            <p className="hint">
              {oda
                ? "ODA detected · DWG + DXF"
                : "Without ODA · use DXF (or install ODA for DWG)"}
            </p>
          </div>
          <input
            type="file"
            accept=".dwg,.dxf,application/acad,image/vnd.dwg"
            multiple
            hidden
            onChange={(e) => {
              if (e.target.files) acceptFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </label>

        {items.length > 0 && (
          <>
            <div className="progress" aria-hidden>
              <span style={{ width: `${progress}%` }} />
            </div>
            <div className="file-list">
              {items.map((f) => (
                <div className="file-row" key={f.id}>
                  <span className="name" title={f.name}>
                    {f.name}
                  </span>
                  <span className="meta">
                    {formatBytes(f.size)}
                    {f.statsLabel ? ` · ${f.statsLabel}` : ""}
                  </span>
                  <span className={`status status-${f.status === "queued" ? "idle" : f.status === "running" ? "running" : f.status === "ok" ? "ok" : "err"}`}>
                    {f.status === "queued" && "Queued"}
                    {f.status === "running" && "Working…"}
                    {f.status === "ok" && (
                      f.downloadUrl ? (
                        <a className="btn-linkish" href={f.downloadUrl} download>
                          Download
                        </a>
                      ) : (
                        "Done"
                      )
                    )}
                    {f.status === "error" && (f.message || "Error")}
                    {f.status === "queued" && (
                      <button
                        type="button"
                        className="icon-btn"
                        aria-label="Remove"
                        onClick={() => removeItem(f.id)}
                      >
                        ×
                      </button>
                    )}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="actions">
          <button
            type="button"
            className="btn-primary"
            disabled={!canConvert}
            onClick={onConvert}
          >
            {busy
              ? "Converting…"
              : `Translate ${items.length || ""} file${items.length === 1 ? "" : "s"}`.trim()}
          </button>
          {zipUrl && (
            <a className="btn btn-primary" href={zipUrl} download>
              Download all (ZIP)
            </a>
          )}
          <button
            type="button"
            className="btn-ghost"
            disabled={busy}
            onClick={() => {
              setItems([]);
              setZipUrl(null);
              setMessage("Queue cleared.");
            }}
          >
            Clear queue
          </button>
          <button type="button" className="btn-ghost" onClick={refreshHealth}>
            Recheck worker
          </button>
        </div>
      </div>

      <div className="status-box">
        <strong>Status</strong>
        <div>{message}</div>
      </div>
    </>
  );
}
