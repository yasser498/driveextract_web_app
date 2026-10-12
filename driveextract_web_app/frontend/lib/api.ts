export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export type JobItem = {
  index: number;
  url: string;
  status: string;
  name?: string | null;
  pages_total: number;
  pages_done: number;
  pdf_url?: string | null;
  images_zip_url?: string | null;
  error?: string | null;
};

export type Job = {
  id: string;
  status: string;
  progress: number;
  output: string;
  items: JobItem[];
  all_zip_url?: string | null;
};

export async function createJob(payload: unknown) {
  const res = await fetch(`${API_BASE}/api/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ job_id: string }>;
}

export async function getJob(id: string) {
  const res = await fetch(`${API_BASE}/api/jobs/${id}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Job>;
}

export function fileUrl(path?: string | null) {
  return path ? `${API_BASE}${path}` : '#';
}
