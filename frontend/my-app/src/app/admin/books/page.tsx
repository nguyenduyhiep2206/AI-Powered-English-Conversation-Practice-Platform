"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, Loader2, Trash2, Upload } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  BOOK_STATUS_LABELS,
  BOOK_TYPE_LABELS,
  deleteAdminBook,
  fetchAdminBooks,
  formatFileSize,
  uploadAdminBook,
  type Book,
  type BookType,
  type CefrLevel,
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

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !title.trim()) {
      setError("Title and PDF file are required");
      return;
    }

    setUploading(true);
    setError(null);
    try {
      await uploadAdminBook({
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
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
          Upload PDF books for AI indexing and personalized tests.
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
                      <td className="px-5 py-3 text-muted-foreground">{book.chunk_count}</td>
                      <td className="px-5 py-3 text-right">
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
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </>
  );
}
