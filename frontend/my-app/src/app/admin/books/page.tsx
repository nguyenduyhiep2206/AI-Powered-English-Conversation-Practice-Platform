"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, BookOpen, Loader2, ScanSearch, Trash2, Upload } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

const STATUS_BADGE: Record<Book["status"], string> = {
  uploaded: "bg-[#F9F9F8] text-[#787774]",
  needs_review: "bg-[#FBF3DB] text-[#956400]",
  processing: "bg-[#E1F3FE] text-[#1F6C9F]",
  ready: "bg-[#EDF3EC] text-[#346538]",
  failed: "bg-[#FDEBEC] text-[#9F2F2D]",
};

const selectClassName =
  "flex h-9 w-full rounded-[6px] border border-[#EAEAEA] bg-white px-3 text-sm text-[#111111] outline-none focus-visible:border-[#111111] focus-visible:ring-1 focus-visible:ring-[#111111]/50";

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
    for (let i = 0; i < 45; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      try {
        const book = await fetchAdminBook(bookId);
        setBooks((prev) => prev.map((b) => (b.id === bookId ? book : b)));
        if (book.status === "uploaded") {
          continue;
        }
        try {
          const nextPreview = await fetchBookStructurePreview(bookId);
          setPreviewBookId(bookId);
          setPreview(nextPreview);
        } catch {
          /* preview may not exist yet on hard fail */
        }
        if (book.status === "processing") {
          continue;
        }
        return;
      } catch {
        /* keep polling while detect/index runs in background */
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
      <header className="border-b border-[#EAEAEA] px-6 py-8 md:px-10">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[#787774]">
          Content library
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-[#111111]">
          Books
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#787774]">
          Upload a PDF, verify structure, then index. Sync skills and generate quiz
          live on the Quiz page.
        </p>
      </header>

      <main className="mx-auto w-full max-w-8xl flex-1 space-y-8 p-6 md:p-10">
        <section className="rounded-[12px] border border-[#EAEAEA] bg-white p-6 md:p-8">
          <div className="mb-6 flex items-center gap-2">
            <Upload className="h-4 w-4 text-[#111111]" />
            <h2 className="text-sm font-semibold tracking-tight">Upload PDF</h2>
          </div>

          <form className="grid gap-4 md:grid-cols-2" onSubmit={handleUpload}>
            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="book-title">Title</Label>
              <Input
                id="book-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="English Grammar in Use"
                className="rounded-[6px] border-[#EAEAEA] shadow-none"
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
                className="rounded-[6px] border-[#EAEAEA] shadow-none"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="book-type">Book type</Label>
              <select
                id="book-type"
                value={bookType}
                onChange={(e) => setBookType(e.target.value as BookType)}
                className={selectClassName}
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
                className={selectClassName}
              >
                <option value="">Not set</option>
                {CEFR_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="book-file">PDF file</Label>
              <Input
                id="book-file"
                type="file"
                accept="application/pdf,.pdf"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="rounded-[6px] border-[#EAEAEA] shadow-none"
                required
              />
            </div>

            <div className="md:col-span-2">
              <Button
                type="submit"
                disabled={uploading}
                className="rounded-[6px] bg-[#111111] text-white hover:bg-[#333333] active:scale-[0.98]"
              >
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
          <div className="rounded-[8px] border border-[#EAEAEA] bg-[#FDEBEC] px-4 py-3 text-sm text-[#9F2F2D]">
            {error}
          </div>
        )}

        <section className="overflow-hidden rounded-[12px] border border-[#EAEAEA] bg-white">
          <div className="flex items-center gap-2 border-b border-[#EAEAEA] px-6 py-4">
            <BookOpen className="h-4 w-4 text-[#111111]" />
            <h2 className="text-sm font-semibold tracking-tight">Uploaded books</h2>
            <span className="ml-auto rounded-full bg-[#F9F9F8] px-2.5 py-0.5 font-mono text-[11px] text-[#787774]">
              {books.length}
            </span>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16 text-[#787774]">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : books.length === 0 ? (
            <p className="px-6 py-14 text-center text-sm text-[#787774]">
              No books uploaded yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="border-b border-[#EAEAEA] text-[11px] uppercase tracking-[0.08em] text-[#787774]">
                  <tr>
                    <th className="px-5 py-3 font-medium">Title</th>
                    <th className="px-5 py-3 font-medium">Type</th>
                    <th className="px-5 py-3 font-medium">Level</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Pages</th>
                    <th className="px-5 py-3 font-medium">Size</th>
                    <th className="px-5 py-3 font-medium">Chunks</th>
                    <th className="px-5 py-3 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {books.map((book) => (
                    <tr key={book.id} className="border-b border-[#EAEAEA] last:border-0">
                      <td className="px-5 py-3.5">
                        <p className="font-medium text-[#111111]">{book.title}</p>
                        {book.description && (
                          <p className="mt-0.5 line-clamp-1 text-xs text-[#787774]">
                            {book.description}
                          </p>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-[#787774]">
                        {BOOK_TYPE_LABELS[book.book_type]}
                      </td>
                      <td className="px-5 py-3.5 font-mono text-xs text-[#787774]">
                        {book.cefr_level ?? "—"}
                      </td>
                      <td className="px-5 py-3.5">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.05em] ${STATUS_BADGE[book.status]}`}
                        >
                          {BOOK_STATUS_LABELS[book.status]}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 font-mono text-xs text-[#787774]">
                        {book.page_count ?? "—"}
                      </td>
                      <td className="px-5 py-3.5 font-mono text-xs text-[#787774]">
                        {formatFileSize(book.file_size)}
                      </td>
                      <td className="px-5 py-3.5 font-mono text-xs text-[#787774]">
                        {book.chunk_count}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {book.status === "ready" && (
                            <Button
                              type="button"
                              size="sm"
                              asChild
                              className="rounded-[6px] bg-[#111111] text-white hover:bg-[#333333]"
                            >
                              <Link href={`/admin/quiz?bookId=${book.id}`}>
                                Open quiz
                                <ArrowRight className="ml-1 h-3.5 w-3.5" />
                              </Link>
                            </Button>
                          )}
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
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            title="View structure preview"
                            disabled={previewLoading}
                            onClick={() => handleShowPreview(book.id)}
                          >
                            Structure
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
                            className="text-[#9F2F2D] hover:bg-[#FDEBEC] hover:text-[#9F2F2D]"
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
          <section className="rounded-[12px] border border-[#EAEAEA] bg-white p-6 md:p-8">
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold tracking-tight">Structure preview</h2>
              {preview.detection_method && (
                <Badge variant="outline" className="rounded-full font-mono text-[10px]">
                  {preview.detection_method}
                </Badge>
              )}
              {preview.confidence != null && (
                <span className="rounded-full bg-[#F9F9F8] px-2.5 py-0.5 font-mono text-[10px] text-[#787774]">
                  {(preview.confidence * 100).toFixed(0)}% confidence
                </span>
              )}
              <span
                className={`rounded-full px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.05em] ${STATUS_BADGE[preview.status]}`}
              >
                {BOOK_STATUS_LABELS[preview.status]}
              </span>
              {preview.units.length > 0 && preview.status === "needs_review" && (
                <Button
                  type="button"
                  size="sm"
                  className="ml-auto rounded-[6px] bg-[#111111] text-white hover:bg-[#333333]"
                  disabled={indexingId === previewBookId}
                  onClick={() => handleConfirmAndIndex(previewBookId)}
                >
                  {indexingId === previewBookId ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Confirm & index"
                  )}
                </Button>
              )}
            </div>

            {preview.status === "processing" && (
              <p className="mb-3 text-sm text-[#787774]">
                Indexing in background (chunk + embed)…
              </p>
            )}

            {preview.status === "needs_review" && (
              <p className="mb-3 text-sm text-[#787774]">
                Automatic verification did not pass. Retry detect, or Confirm &amp; index
                to proceed with the units below.
              </p>
            )}

            {preview.units.length === 0 ? (
              <p className="text-sm text-[#787774]">
                {preview.status === "uploaded"
                  ? "Detecting & merging structure in the background…"
                  : "No structure units yet. Use Retry detect if detection failed."}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="border-b border-[#EAEAEA] text-[11px] uppercase tracking-[0.08em] text-[#787774]">
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
                      <tr
                        key={unit.id ?? unit.unit_index}
                        className="border-b border-[#EAEAEA] last:border-0"
                      >
                        <td className="px-3 py-2.5 font-mono text-xs text-[#787774]">
                          {unit.unit_index + 1}
                        </td>
                        <td className="px-3 py-2.5 font-medium">{unit.title}</td>
                        <td className="px-3 py-2.5 font-mono text-xs text-[#787774]">
                          {unit.page_start}–{unit.page_end}
                        </td>
                        <td className="px-3 py-2.5 text-[#787774]">
                          {unit.depth_or_source ?? "—"}
                        </td>
                        <td className="px-3 py-2.5 text-right">
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
      </main>
    </>
  );
}
