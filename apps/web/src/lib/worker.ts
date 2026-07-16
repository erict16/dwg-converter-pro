export type ConvertFileResult = {
  original_name: string;
  ok: boolean;
  output_name?: string | null;
  error?: string | null;
  stats?: {
    strings_seen?: number;
    glossary_hits?: number;
    mt_calls?: number;
    unchanged?: number;
  };
  process?: {
    entities_touched?: number;
    chinese_found?: number;
    change_count?: number;
  };
  download_path?: string | null;
};

export type ConvertResponse = {
  ok: boolean;
  job_id: string;
  results: ConvertFileResult[];
  zip_url?: string | null;
  oda?: boolean;
  error?: string;
};

export function workerBase(): string {
  return (
    process.env.NEXT_PUBLIC_WORKER_URL?.replace(/\/$/, "") ||
    "http://127.0.0.1:8000"
  );
}

export async function fetchHealth(): Promise<{
  ok: boolean;
  oda?: boolean;
  accepts?: string[];
  version?: string;
}> {
  const r = await fetch(`${workerBase()}/health`, { cache: "no-store" });
  if (!r.ok) throw new Error(`Worker health ${r.status}`);
  return r.json();
}

export async function convertFiles(files: File[]): Promise<ConvertResponse> {
  const fd = new FormData();
  for (const f of files) {
    fd.append("files", f, f.name);
  }
  const r = await fetch(`${workerBase()}/v1/convert`, {
    method: "POST",
    body: fd,
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || `Convert failed (${r.status})`);
  }
  return r.json();
}

export function absoluteWorkerUrl(path: string): string {
  if (path.startsWith("http")) return path;
  return `${workerBase()}${path.startsWith("/") ? "" : "/"}${path}`;
}
