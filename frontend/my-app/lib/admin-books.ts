import { authFetch, authFetchMultipart, extractErrorMessage } from "@/lib/api";

export type BookStatus = "uploaded" | "needs_review" | "processing" | "ready" | "failed";
export type BookType =
  | "grammar_textbook"
  | "reading_practice"
  | "test_bank"
  | "freeform";
export type CefrLevel = "A1" | "A2" | "B1" | "B2" | "C1";

export type Book = {
  id: number;
  title: string;
  description?: string | null;
  cefr_level?: CefrLevel | null;
  book_type: BookType;
  detection_method?: string | null;
  file_path: string;
  file_public_id?: string | null; // Supabase storage object path
  file_size: number;
  page_count?: number | null;
  status: BookStatus;
  uploaded_by?: number | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
};

type BookListResponse = { success: boolean; data: Book[] };
type BookResponse = { success: boolean; data: Book };

export async function fetchAdminBooks(): Promise<Book[]> {
  const res = await authFetch("/api/v1/admin/books");
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load books"));
  }
  const body = (await res.json()) as BookListResponse;
  return body.data;
}

export async function fetchAdminBook(bookId: number): Promise<Book> {
  const res = await authFetch(`/api/v1/admin/books/${bookId}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load book"));
  }
  const body = (await res.json()) as BookResponse;
  return body.data;
}

export async function uploadAdminBook(payload: {
  file: File;
  title: string;
  book_type: BookType;
  description?: string;
  cefr_level?: CefrLevel;
}): Promise<Book> {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("title", payload.title);
  formData.append("book_type", payload.book_type);
  if (payload.description) formData.append("description", payload.description);
  if (payload.cefr_level) formData.append("cefr_level", payload.cefr_level);

  const res = await authFetchMultipart("/api/v1/admin/books/upload", formData);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to upload book"));
  }
  const body = (await res.json()) as BookResponse;
  return body.data;
}

export async function deleteAdminBook(bookId: number): Promise<void> {
  const res = await authFetch(`/api/v1/admin/books/${bookId}`, { method: "DELETE" });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to delete book"));
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const BOOK_STATUS_LABELS: Record<BookStatus, string> = {
  uploaded: "Uploaded",
  needs_review: "Needs review",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

export const BOOK_TYPE_LABELS: Record<BookType, string> = {
  grammar_textbook: "Grammar textbook",
  reading_practice: "Reading practice",
  test_bank: "Test bank",
  freeform: "Freeform",
};

export type StructureUnitPreview = {
  id: number;
  unit_index: number;
  title: string;
  page_start: number;
  page_end: number;
  detection_method: string;
  confidence: number;
  depth_or_source?: string | null;
};

export type StructurePreview = {
  book_id: number;
  detection_method?: string | null;
  confidence?: number | null;
  status: BookStatus;
  units: StructureUnitPreview[];
};

type StructurePreviewResponse = { success: boolean; data: StructurePreview };

export async function detectBookStructure(bookId: number): Promise<StructurePreview> {
  const res = await authFetch(`/api/v1/admin/books/${bookId}/detect-structure`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to detect book structure"));
  }
  const body = (await res.json()) as StructurePreviewResponse;
  return body.data;
}

export async function fetchBookStructurePreview(bookId: number): Promise<StructurePreview> {
  const res = await authFetch(`/api/v1/admin/books/${bookId}/structure-preview`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load structure preview"));
  }
  const body = (await res.json()) as StructurePreviewResponse;
  return body.data;
}

export async function confirmAndIndexBook(bookId: number): Promise<Book> {
  const res = await authFetch(`/api/v1/admin/books/${bookId}/confirm-and-index`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to start indexing"));
  }
  const body = (await res.json()) as BookResponse;
  return body.data;
}

export async function reindexBookUnit(bookId: number, unitId: number): Promise<Book> {
  const res = await authFetch(`/api/v1/admin/books/${bookId}/reindex-unit/${unitId}`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to reindex unit"));
  }
  const body = (await res.json()) as BookResponse;
  return body.data;
}

export async function retryBookEmbeddings(bookId: number): Promise<Book> {
  const res = await authFetch(`/api/v1/admin/books/${bookId}/retry-embeddings`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to retry embeddings"));
  }
  const body = (await res.json()) as BookResponse;
  return body.data;
}
