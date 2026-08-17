export type DocumentStatus = "processing" | "ready" | "failed";

export interface DocumentRecord {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: DocumentStatus;
  chunk_count: number;
  created_at: string;
  error: string | null;
  duplicate: boolean;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  filename: string;
  chunk_index: number;
  page_number: number | null;
  char_start: number;
  char_end: number;
  quote: string;
}

export interface AnswerResponse {
  query: string;
  status: "answered" | "insufficient_evidence";
  answer: string;
  citations: Citation[];
  retrieved_chunk_count: number;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.ok) return response.json() as Promise<T>;

  let message = `Request failed (${response.status})`;
  try {
    const body = (await response.json()) as { detail?: string | Array<{ msg: string }> };
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) message = body.detail.map((item) => item.msg).join(", ");
  } catch {
    // Keep the status-based message when the server does not return JSON.
  }
  throw new Error(message);
}

export async function listDocuments(signal?: AbortSignal): Promise<DocumentRecord[]> {
  const response = await fetch(`${API_BASE_URL}/documents`, { signal });
  const body = await parseResponse<{ documents: DocumentRecord[] }>(response);
  return body.documents;
}

export async function uploadDocument(file: File): Promise<DocumentRecord> {
  const body = new FormData();
  body.append("file", file);
  return parseResponse<DocumentRecord>(
    await fetch(`${API_BASE_URL}/documents`, { method: "POST", body }),
  );
}

export async function askQuestion(query: string, documentIds: string[]): Promise<AnswerResponse> {
  return parseResponse<AnswerResponse>(
    await fetch(`${API_BASE_URL}/answers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, document_ids: documentIds, top_k: 5 }),
    }),
  );
}
