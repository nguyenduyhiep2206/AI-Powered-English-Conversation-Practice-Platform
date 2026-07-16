"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, Loader2, ScanSearch, Trash2, Upload } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { BookQuizPanel } from "@/components/admin/BookQuizPanel";
import {
  BOOK_STATUS_LABELS,
  BOOK_TYPE_LABELS,
  confirmAndIndexBook,
  deleteAdminBook,
  detectBookStructure,
  fetchAdminBook,
  fetchAdminBooks,
  fetchBookStructurePreview,
  formatFileSize,
  reindexBookUnit,
  retryBookEmbeddings,
  uploadAdminBook,
  type Book,
  type BookType,
  type CefrLevel,
  type StructurePreview,
} from "@/lib/admin-books";

const CEFR_LEVELS: CefrLevel[] = ["A1", "A2", "B1", "B2", "C1"];
const BOOK_TYPES: BookType[] = [
  "grammar_textbook",
  "reading_practice",
  "test_bank",
  "freeform",
];

const STATUS_VARIANT: Record<Book["status"], "default" | "secondary" | "outline" | "destructive"> = {
  uploaded: "secondary",
  needs_review: "outline",
  processing: "outline",
  ready: "default",
  failed: "destructive",
};

export default function AdminBooksPage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [detectingId, setDetectingId] = useState<number | null>(null);
  const [indexingId, setIndexingId] = useState<number | null>(null);
  const [reindexingUnitId, setReindexingUnitId] = useState<number | null>(null);
  const [retryingEmbedId, setRetryingEmbedId] = useState<number | null>(null);
  const [previewBookId, setPreviewBookId] = useState<number | null>(null);
  const [preview, setPreview] = useState<StructurePreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [cefrLevel, setCefrLevel] = useState<CefrLevel | "">("");
  const [bookType, setBookType] = useState<BookType>("grammar_textbook");
  const [file, setFile] = useState<File | null>(null);

  const loadBooks = useCallback(async () => {
    setError(null);
    try {
      const data = await fetchAdminBooks();
      setBooks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load books");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBooks();
  }, [loadBooks]);

  async function pollUntilDetectSettled(bookId: number) {
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      try {
        const book = await fetchAdminBook(bookId);
        setBooks((prev) => prev.map((b) => (b.id === bookId ? book : b)));
        if (book.status !== "uploaded") {
          if (book.status === "needs_review") {
            const nextPreview = await fetchBookStructurePreview(bookId);
            setPreviewBookId(bookId);
            setPreview(nextPreview);
          }
          return;
        }
      } catch {
        /* keep polling while detect runs in background */
      }
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !title.trim()) {
      setError("Title and PDF file are required");
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const book = await uploadAdminBook({
        file,
        title: title.trim(),
        book_type: bookType,
        description: description.trim() || undefined,
        cefr_level: cefrLevel || undefined,
      });
      setTitle("");
      setDescription("");
      setCefrLevel("");
      setFile(null);
      const input = document.getElementById("book-file") as HTMLInputElement | null;
      if (input) input.value = "";
      await loadBooks();
      void pollUntilDetectSettled(book.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(bookId: number) {
    if (!window.confirm("Delete this book?")) return;

    setDeletingId(bookId);
    setError(null);
    try {
      await deleteAdminBook(bookId);
      setBooks((prev) => prev.filter((book) => book.id !== bookId));
      if (previewBookId === bookId) {
        setPreviewBookId(null);
        setPreview(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleDetect(bookId: number) {
    setDetectingId(bookId);
    setError(null);
    try {
      const result = await detectBookStructure(bookId);
      setPreviewBookId(bookId);
      setPreview(result);
      await loadBooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Structure detection failed");
    } finally {
      setDetectingId(null);
    }
  }

  async function handleShowPreview(bookId: number) {
    if (previewBookId === bookId && preview) {
      setPreviewBookId(null);
      setPreview(null);
      return;
    }

    setPreviewLoading(true);
    setError(null);
    try {
      const result = await fetchBookStructurePreview(bookId);
      setPreviewBookId(bookId);
      setPreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load preview");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleConfirmAndIndex(bookId: number) {
    if (!window.confirm("Confirm structure and start indexing?")) return;
    setIndexingId(bookId);
    setError(null);
    try {
      await confirmAndIndexBook(bookId);
      await loadBooks();
      const result = await fetchBookStructurePreview(bookId);
      setPreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Indexing failed to start");
    } finally {
      setIndexingId(null);
    }
  }

  async function handleReindexUnit(bookId: number, unitId: number) {
    setReindexingUnitId(unitId);
    setError(null);
    try {
      await reindexBookUnit(bookId, unitId);
      await loadBooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reindex unit failed");
    } finally {
      setReindexingUnitId(null);
    }
  }

  async function handleRetryEmbeddings(bookId: number) {
    setRetryingEmbedId(bookId);
    setError(null);
    try {
      await retryBookEmbeddings(bookId);
      await loadBooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retry embeddings failed");
    } finally {
      setRetryingEmbedId(null);
    }
  }

  return (
    <>
      <header className="border-b border-border px-6 py-5">
        <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          Content library
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Books</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload a PDF — structure is detected automatically. Review units, then confirm
          to chunk &amp; embed.
        </p>
      </header>

      <main className="flex-1 space-y-6 p-6">
        <section className="ef-card rounded-xl border border-border bg-card/60 p-5">
          <div className="mb-4 flex items-center gap-2">
            <Upload className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold">Upload PDF</h2>
          </div>

          <form className="grid gap-4 md:grid-cols-2" onSubmit={handleUpload}>
            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="book-title">Title</Label>
              <Input
                id="book-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="English Grammar in Use"
                required
              />
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="book-description">Description (optional)</Label>
              <Input
                id="book-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="B1 grammar reference for workplace learners"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="book-type">Book type</Label>
              <select
                id="book-type"
                value={bookType}
                onChange={(e) => setBookType(e.target.value as BookType)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent dark:bg-zinc-900 px-3 text-zinc-950 dark:text-zinc-50 px-3 text-black text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
                required
              >
                {BOOK_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {BOOK_TYPE_LABELS[type]}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="book-level">CEFR level (optional)</Label>
              <select
                id="book-level"
                value={cefrLevel}
                onChange={(e) => setCefrLevel(e.target.value as CefrLevel | "")}
                className="flex h-9 w-full rounded-md border border-input bg-transparent dark:bg-zinc-900 px-3 text-zinc-950 dark:text-zinc-50 px-3 text-black text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
              >
                <option value="">Not set</option>
                {CEFR_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="book-file">PDF file</Label>
              <Input
                id="book-file"
                type="file"
                accept="application/pdf,.pdf"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                required
              />
            </div>

            <div className="md:col-span-2">
              <Button type="submit" disabled={uploading}>
                {uploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Upload className="mr-1.5 h-4 w-4" />
                    Upload book
                  </>
                )}
              </Button>
            </div>
          </form>
        </section>

        {error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        <section className="ef-card overflow-hidden rounded-xl border border-border bg-card/60">
          <div className="flex items-center gap-2 border-b border-border px-5 py-4">
            <BookOpen className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold">Uploaded books</h2>
            <Badge variant="outline" className="ml-auto">
              {books.length}
            </Badge>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : books.length === 0 ? (
            <p className="px-5 py-10 text-center text-sm text-muted-foreground">
              No books uploaded yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="border-b border-border bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-5 py-3 font-medium">Title</th>
                    <th className="px-5 py-3 font-medium">Type</th>
                    <th className="px-5 py-3 font-medium">Level</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Pages</th>
                    <th className="px-5 py-3 font-medium">Size</th>
                    <th className="px-5 py-3 font-medium">Detection</th>
                    <th className="px-5 py-3 font-medium">Chunks</th>
                    <th className="px-5 py-3 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {books.map((book) => (
                    <tr key={book.id} className="border-b border-border/70 last:border-0">
                      <td className="px-5 py-3">
                        <p className="font-medium text-foreground">{book.title}</p>
                        {book.description && (
                          <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                            {book.description}
                          </p>
                        )}
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">
                        {BOOK_TYPE_LABELS[book.book_type]}
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">
                        {book.cefr_level ?? "—"}
                      </td>
                      <td className="px-5 py-3">
                        <Badge variant={STATUS_VARIANT[book.status]}>
                          {BOOK_STATUS_LABELS[book.status]}
                        </Badge>
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">
                        {book.page_count ?? "—"}
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">
                        {formatFileSize(book.file_size)}
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">
                        {book.detection_method ?? "—"}
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">{book.chunk_count}</td>
                      <td className="px-5 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            title="Retry structure detect"
                            disabled={
                              detectingId === book.id ||
                              previewLoading ||
                              book.status === "uploaded" ||
                              book.status === "processing"
                            }
                            onClick={() => handleDetect(book.id)}
                          >
                            {detectingId === book.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <ScanSearch className="h-4 w-4" />
                            )}
                            <span className="ml-1 hidden sm:inline">Retry detect</span>
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            title="View structure preview"
                            disabled={previewLoading}
                            onClick={() => handleShowPreview(book.id)}
                          >
                            Preview
                          </Button>
                          {(book.status === "ready" || book.status === "failed") && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              title="Retry pending Voyage embeddings"
                              disabled={retryingEmbedId === book.id}
                              onClick={() => handleRetryEmbeddings(book.id)}
                            >
                              {retryingEmbedId === book.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                "Retry embed"
                              )}
                            </Button>
                          )}
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                            disabled={deletingId === book.id}
                            onClick={() => handleDelete(book.id)}
                          >
                            {deletingId === book.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {preview && previewBookId !== null && (
          <section className="ef-card rounded-xl border border-border bg-card/60 p-5">
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold">Structure preview</h2>
              {preview.detection_method && (
                <Badge variant="outline">{preview.detection_method}</Badge>
              )}
              {preview.confidence != null && (
                <Badge variant="secondary">
                  Confidence {(preview.confidence * 100).toFixed(0)}%
                </Badge>
              )}
              <Badge variant={STATUS_VARIANT[preview.status]}>
                {BOOK_STATUS_LABELS[preview.status]}
              </Badge>
              {preview.units.length > 0 && (
                <Button
                  type="button"
                  size="sm"
                  className="ml-auto"
                  disabled={
                    indexingId === previewBookId ||
                    preview.status === "processing" ||
                    preview.status === "uploaded"
                  }
                  onClick={() => handleConfirmAndIndex(previewBookId)}
                >
                  {indexingId === previewBookId || preview.status === "processing" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Confirm & index"
                  )}
                </Button>
              )}
            </div>

            {preview.status === "processing" && (
              <p className="mb-3 text-sm text-muted-foreground">
                Indexing in background (chunk + embed)…
              </p>
            )}

            {preview.units.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {preview.status === "uploaded"
                  ? "Detecting structure in the background…"
                  : "No structure units yet. Use Retry detect if detection failed."}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 font-medium">#</th>
                      <th className="px-3 py-2 font-medium">Title</th>
                      <th className="px-3 py-2 font-medium">Pages</th>
                      <th className="px-3 py-2 font-medium">Source</th>
                      <th className="px-3 py-2 font-medium" />
                    </tr>
                  </thead>
                  <tbody>
                    {preview.units.map((unit) => (
                      <tr key={unit.id ?? unit.unit_index} className="border-b border-border/70 last:border-0">
                        <td className="px-3 py-2 text-muted-foreground">{unit.unit_index + 1}</td>
                        <td className="px-3 py-2 font-medium">{unit.title}</td>
                        <td className="px-3 py-2 text-muted-foreground">
                          {unit.page_start}–{unit.page_end}
                        </td>
                        <td className="px-3 py-2 text-muted-foreground">
                          {unit.depth_or_source ?? "—"}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            disabled={reindexingUnitId === unit.id}
                            onClick={() => handleReindexUnit(previewBookId, unit.id)}
                          >
                            {reindexingUnitId === unit.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              "Reindex"
                            )}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {preview && previewBookId !== null && preview.status === "ready" && (
          <BookQuizPanel
            bookId={previewBookId}
            units={preview.units.map((unit) => ({ id: unit.id, title: unit.title }))}
            onError={setError}
          />
        )}
      </main>
    </>
  );
}
