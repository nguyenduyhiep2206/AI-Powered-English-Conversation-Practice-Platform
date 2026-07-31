"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { BookQuizPanel } from "@/components/admin/BookQuizPanel";
import {
  BOOK_TYPE_LABELS,
  fetchAdminBooks,
  fetchBookStructurePreview,
  type Book,
  type StructurePreview,
} from "@/lib/admin-books";

function AdminQuizPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const bookIdParam = searchParams.get("bookId");

  const [books, setBooks] = useState<Book[]>([]);
  const [loadingBooks, setLoadingBooks] = useState(true);
  const [selectedBookId, setSelectedBookId] = useState<number | null>(null);
  const [preview, setPreview] = useState<StructurePreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const readyBooks = useMemo(
    () => books.filter((book) => book.status === "ready"),
    [books],
  );

  const selectedBook = useMemo(
    () => readyBooks.find((book) => book.id === selectedBookId) ?? null,
    [readyBooks, selectedBookId],
  );

  const loadBooks = useCallback(async () => {
    setError(null);
    try {
      const data = await fetchAdminBooks();
      setBooks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load books");
    } finally {
      setLoadingBooks(false);
    }
  }, []);

  useEffect(() => {
    void loadBooks();
  }, [loadBooks]);

  useEffect(() => {
    if (loadingBooks) return;

    const fromQuery = bookIdParam ? Number(bookIdParam) : NaN;
    if (Number.isFinite(fromQuery) && readyBooks.some((b) => b.id === fromQuery)) {
      setSelectedBookId(fromQuery);
      return;
    }

    if (selectedBookId != null && readyBooks.some((b) => b.id === selectedBookId)) {
      return;
    }

    setSelectedBookId(readyBooks[0]?.id ?? null);
  }, [bookIdParam, loadingBooks, readyBooks, selectedBookId]);

  useEffect(() => {
    if (selectedBookId == null) {
      setPreview(null);
      return;
    }

    let active = true;
    setLoadingPreview(true);
    setError(null);

    fetchBookStructurePreview(selectedBookId)
      .then((result) => {
        if (!active) return;
        setPreview(result);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setPreview(null);
        setError(err instanceof Error ? err.message : "Failed to load book structure");
      })
      .finally(() => {
        if (active) setLoadingPreview(false);
      });

    return () => {
      active = false;
    };
  }, [selectedBookId]);

  function handleSelectBook(bookId: number) {
    setSelectedBookId(bookId);
    router.replace(`/admin/quiz?bookId=${bookId}`);
  }

  return (
    <>
      <header className="border-b border-[#EAEAEA] px-6 py-8 md:px-10">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[#787774]">
          Content pipeline
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-[#111111]">
          Quiz
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#787774]">
          Pick an indexed book, sync skills from its units, generate draft questions,
          then publish.
        </p>
      </header>

      <main className="mx-auto w-full flex-1 space-y-8 p-6 md:p-10">
        <ol className="grid gap-3 sm:grid-cols-3">
          {[
            { step: "01", label: "Sync skills", hint: "Map units → skill graph" },
            { step: "02", label: "Generate", hint: "Draft questions per skill" },
            { step: "03", label: "Publish", hint: "Select drafts → live" },
          ].map((item) => (
            <li
              key={item.step}
              className="rounded-[12px] border border-[#EAEAEA] bg-white px-5 py-4"
            >
              <p className="font-mono text-[11px] tracking-[0.08em] text-[#787774]">
                {item.step}
              </p>
              <p className="mt-1 text-sm font-semibold tracking-tight text-[#111111]">
                {item.label}
              </p>
              <p className="mt-0.5 text-xs text-[#787774]">{item.hint}</p>
            </li>
          ))}
        </ol>

        <section className="rounded-[12px] border border-[#EAEAEA] bg-white p-6 md:p-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="min-w-0 flex-1 space-y-1.5">
              <label
                htmlFor="quiz-book"
                className="text-xs font-medium uppercase tracking-[0.08em] text-[#787774]"
              >
                Indexed book
              </label>
              {loadingBooks ? (
                <div className="flex h-10 items-center text-[#787774]">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              ) : readyBooks.length === 0 ? (
                <p className="text-sm text-[#787774]">
                  No ready books yet.{" "}
                  <Link
                    href="/admin/books"
                    className="font-medium text-[#111111] underline-offset-4 hover:underline"
                  >
                    Upload and index a book
                  </Link>{" "}
                  first.
                </p>
              ) : (
                <select
                  id="quiz-book"
                  value={selectedBookId ?? ""}
                  onChange={(e) => handleSelectBook(Number(e.target.value))}
                  className="flex h-10 w-full max-w-md rounded-[6px] border border-[#EAEAEA] bg-white px-3 text-sm text-[#111111] outline-none focus-visible:border-[#111111] focus-visible:ring-1 focus-visible:ring-[#111111]/50"
                >
                  {readyBooks.map((book) => (
                    <option key={book.id} value={book.id}>
                      {book.title}
                      {book.cefr_level ? ` · ${book.cefr_level}` : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <Link
              href="/admin/books"
              className="inline-flex items-center gap-1.5 text-sm text-[#787774] transition-colors hover:text-[#111111]"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to books
            </Link>
          </div>

          {selectedBook && (
            <p className="mt-4 text-sm text-[#787774]">
              <span className="font-medium text-[#111111]">{selectedBook.title}</span>
              {" · "}
              {BOOK_TYPE_LABELS[selectedBook.book_type]}
              {selectedBook.cefr_level ? ` · ${selectedBook.cefr_level}` : ""}
              {" · "}
              <span className="font-mono text-xs">{selectedBook.chunk_count} chunks</span>
            </p>
          )}
        </section>

        {error && (
          <div className="rounded-[8px] border border-[#EAEAEA] bg-[#FDEBEC] px-4 py-3 text-sm text-[#9F2F2D]">
            {error}
          </div>
        )}

        {selectedBookId != null && loadingPreview && (
          <div className="flex items-center justify-center py-16 text-[#787774]">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        )}

        {selectedBookId != null && !loadingPreview && preview && (
          <BookQuizPanel
            bookId={selectedBookId}
            units={preview.units.map((unit) => ({ id: unit.id, title: unit.title }))}
            onError={setError}
          />
        )}
      </main>
    </>
  );
}

export default function AdminQuizPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-1 items-center justify-center py-24 text-[#787774]">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      }
    >
      <AdminQuizPageInner />
    </Suspense>
  );
}
