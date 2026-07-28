"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import LogoutButton from "@/components/ui/LogoutButton";
import { fetchOnboardingStatus } from "@/lib/onboarding-status";
import {
  advancePlacementSection,
  completePlacementSession,
  fetchPlacementAccessStatus,
  getCurrentPlacementSession,
  startPlacementSession,
  submitReadingAnswers,
  submitWritingAnswer,
  type PlacementFormItem,
  type PlacementSession,
} from "@/lib/placement";
import { assembleRoadmap } from "@/lib/roadmap";

const R5_PAGE_SIZE = 10;

type ReadingPage = {
  key: string;
  label: string;
  passage: string | null;
  items: PlacementFormItem[];
};

function useCountdown(endsAt: string | null | undefined) {
  const [left, setLeft] = useState<number | null>(null);
  useEffect(() => {
    if (!endsAt) {
      setLeft(null);
      return;
    }
    const tick = () => {
      const ms = new Date(endsAt).getTime() - Date.now();
      setLeft(Math.max(0, Math.floor(ms / 1000)));
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [endsAt]);
  return left;
}

function formatTime(sec: number | null) {
  if (sec == null) return "--:--";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function buildReadingPages(
  items: PlacementFormItem[],
  passages: Record<string, { body?: string }>,
): ReadingPage[] {
  const pages: ReadingPage[] = [];
  let i = 0;
  let r5Buffer: PlacementFormItem[] = [];
  const seenIds = new Set<number>();
  const uniqueItems = items.filter((it) => {
    if (seenIds.has(it.id)) return false;
    seenIds.add(it.id);
    return true;
  });

  const flushR5 = () => {
    while (r5Buffer.length > 0) {
      const chunk = r5Buffer.splice(0, R5_PAGE_SIZE);
      pages.push({
        key: `r5-${pages.length}`,
        label: `Part 5 · Incomplete sentences (${chunk.length})`,
        passage: null,
        items: chunk,
      });
    }
  };

  while (i < uniqueItems.length) {
    const item = uniqueItems[i];
    const part = item.toeic_part ?? "";
    if (part === "r5" || !item.passage_id) {
      r5Buffer.push(item);
      i += 1;
      continue;
    }
    flushR5();
    const pid = item.passage_id;
    const group: PlacementFormItem[] = [];
    while (i < uniqueItems.length && uniqueItems[i].passage_id === pid) {
      group.push(uniqueItems[i]);
      i += 1;
    }
    pages.push({
      key: `p-${pid}-${pages.length}`,
      label: `Part ${(part || "R").toUpperCase()} · Passage set (${group.length} Q)`,
      passage: passages[String(pid)]?.body ?? null,
      items: group,
    });
  }
  flushR5();
  return pages;
}

function draftKey(attemptId: number) {
  return `placement-draft-${attemptId}`;
}

type LocalDraft = {
  reading?: Record<string, string>;
  writingTextById?: Record<string, string>;
};

function loadDraft(attemptId: number): LocalDraft {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(draftKey(attemptId));
    if (!raw) return {};
    const parsed = JSON.parse(raw) as LocalDraft;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function saveDraft(attemptId: number, draft: LocalDraft) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(draftKey(attemptId), JSON.stringify(draft));
  } catch {
    /* ignore quota */
  }
}

function clearDraft(attemptId: number) {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(draftKey(attemptId));
  } catch {
    /* ignore */
  }
}

function savedAnswersToMap(saved?: Record<string, string> | null): Record<number, string> {
  const out: Record<number, string> = {};
  if (!saved) return out;
  for (const [k, v] of Object.entries(saved)) {
    const id = Number(k);
    if (Number.isFinite(id) && v) out[id] = v;
  }
  return out;
}

function firstIncompleteReadingPage(
  pages: ReadingPage[],
  answers: Record<number, string>,
): number {
  for (let i = 0; i < pages.length; i += 1) {
    const incomplete = pages[i].items.some((it) => !answers[it.id]);
    if (incomplete) return i;
  }
  return Math.max(0, pages.length - 1);
}

function firstIncompleteWritingIndex(
  items: PlacementFormItem[],
  answers: Record<number, string>,
): number {
  for (let i = 0; i < items.length; i += 1) {
    if (!answers[items[i].id]) return i;
  }
  return Math.max(0, items.length - 1);
}

export default function PlacementPage() {
  const router = useRouter();
  const [session, setSession] = useState<PlacementSession | null>(null);
  const [readingAnswers, setReadingAnswers] = useState<Record<number, string>>({});
  const [pageIndex, setPageIndex] = useState(0);
  const [writingIndex, setWritingIndex] = useState(0);
  const [writingText, setWritingText] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [assembling, setAssembling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadStarted = useRef(false);
  const left = useCountdown(session?.section_ends_at);

  const readingItems = session?.form?.reading_items ?? [];
  const writingItems = session?.form?.writing_items ?? [];
  const passages = session?.form?.passages ?? {};
  const readingPages = useMemo(
    () => buildReadingPages(readingItems, passages),
    [readingItems, passages],
  );
  const currentPage = readingPages[pageIndex];
  const currentWriting = writingItems[writingIndex];
  const writingPassage =
    currentWriting?.passage_id != null
      ? passages[String(currentWriting.passage_id)]?.body ?? null
      : null;

  const readingAnswered = Object.keys(readingAnswers).length;
  const readingProgress =
    readingItems.length > 0 ? Math.round((readingAnswered / readingItems.length) * 100) : 0;

  function hydrateFromSession(next: PlacementSession) {
    const serverMap = savedAnswersToMap(next.saved_answers);
    const draft = loadDraft(next.attempt_id);
    const mergedReading: Record<number, string> = { ...serverMap };
    if (draft.reading) {
      for (const [k, v] of Object.entries(draft.reading)) {
        const id = Number(k);
        if (Number.isFinite(id) && v && !mergedReading[id]) {
          mergedReading[id] = v;
        }
      }
    }
    setSession(next);
    setReadingAnswers(mergedReading);

    const pages = buildReadingPages(
      next.form?.reading_items ?? [],
      next.form?.passages ?? {},
    );
    const wItems = next.form?.writing_items ?? [];

    if (next.section === "writing") {
      const wIdx = firstIncompleteWritingIndex(wItems, serverMap);
      setWritingIndex(wIdx);
      const wId = wItems[wIdx]?.id;
      const fromServer = wId != null ? serverMap[wId] : "";
      const fromDraft =
        wId != null ? draft.writingTextById?.[String(wId)] ?? "" : "";
      setWritingText(fromServer || fromDraft || "");
      setPageIndex(Math.max(0, pages.length - 1));
    } else {
      setPageIndex(firstIncompleteReadingPage(pages, mergedReading));
      setWritingIndex(0);
      setWritingText("");
    }
  }

  function persistReadingDraft(nextAnswers: Record<number, string>) {
    if (!session) return;
    const draft = loadDraft(session.attempt_id);
    const reading: Record<string, string> = {};
    for (const [id, val] of Object.entries(nextAnswers)) {
      reading[String(id)] = val;
    }
    saveDraft(session.attempt_id, { ...draft, reading });
  }

  function persistWritingDraft(itemId: number, text: string) {
    if (!session) return;
    const draft = loadDraft(session.attempt_id);
    saveDraft(session.attempt_id, {
      ...draft,
      writingTextById: {
        ...(draft.writingTextById ?? {}),
        [String(itemId)]: text,
      },
    });
  }

  useEffect(() => {
    if (loadStarted.current) return;
    loadStarted.current = true;

    async function load() {
      try {
        const status = await fetchOnboardingStatus();
        if (!status.survey_done) {
          router.replace("/onboarding");
          return;
        }
        const access = await fetchPlacementAccessStatus().catch(() => null);
        const canEnter =
          !status.placement_done || Boolean(access?.has_in_progress);
        if (!canEnter) {
          router.replace("/dashboard");
          return;
        }
        let next = await getCurrentPlacementSession();
        if (!next) next = await startPlacementSession();
        const readingCount = next.form?.reading_items?.length ?? 0;
        if (!next.done && readingCount === 0) {
          next = await startPlacementSession();
        }
        if (!next.done && (next.form?.reading_items?.length ?? 0) === 0) {
          setError(
            "Placement bank has no published TOEIC questions yet. Ask an admin to generate/publish or run seed_toeic_placement.",
          );
        }
        if (next.done) {
          clearDraft(next.attempt_id);
          setSession(next);
        } else {
          hydrateFromSession(next);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load placement");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  async function saveReadingPage() {
    if (!session || !currentPage) return;
    const missing = currentPage.items.filter((it) => !readingAnswers[it.id]);
    if (missing.length > 0) {
      setError(`Answer all ${missing.length} question(s) on this page`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const payload = currentPage.items.map((it) => ({
        item_id: it.id,
        given_answer: readingAnswers[it.id],
      }));
      const next = await submitReadingAnswers(session.attempt_id, payload);
      hydrateFromSession(next);
      const pages = buildReadingPages(
        next.form?.reading_items ?? [],
        next.form?.passages ?? {},
      );
      const answers = savedAnswersToMap(next.saved_answers);
      const draft = loadDraft(next.attempt_id);
      if (draft.reading) {
        for (const [k, v] of Object.entries(draft.reading)) {
          const id = Number(k);
          if (Number.isFinite(id) && v && !answers[id]) answers[id] = v;
        }
      }
      const nextPage = firstIncompleteReadingPage(pages, answers);
      setPageIndex(nextPage);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submit failed");
    } finally {
      setBusy(false);
    }
  }

  async function goWriting() {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const next = await advancePlacementSection(session.attempt_id);
      hydrateFromSession(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot advance yet — finish Reading");
    } finally {
      setBusy(false);
    }
  }

  async function saveWriting() {
    if (!session || !currentWriting) return;
    setBusy(true);
    setError(null);
    try {
      const next = await submitWritingAnswer(session.attempt_id, {
        item_id: currentWriting.id,
        text: writingText,
      });
      hydrateFromSession(next);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Writing submit failed");
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const next = await completePlacementSession(session.attempt_id);
      clearDraft(next.attempt_id);
      setSession(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Complete failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleAssembleRoadmap() {
    setAssembling(true);
    setError(null);
    try {
      await assembleRoadmap();
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assemble roadmap");
    } finally {
      setAssembling(false);
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f7f4ef] text-[#1c1917]">
        <Loader2 className="h-6 w-6 animate-spin" />
      </main>
    );
  }

  if (session?.done) {
    return (
      <main className="min-h-screen bg-[#f7f4ef] px-6 py-10 text-[#1c1917]">
        <div className="mx-auto max-w-xl space-y-6">
          <div className="flex justify-end">
            <LogoutButton />
          </div>
          <h1 className="font-serif text-3xl">Placement complete</h1>
          <p className="text-stone-600">
            Level <strong>{session.current_level}</strong> · sub-level{" "}
            <strong>{session.placement_score}</strong>
          </p>
          <p className="text-sm text-stone-600">
            Reading {session.reading_scale} · Writing {session.writing_scale}
          </p>
          {session.writing_feedback && session.writing_feedback.length > 0 && (
            <ul className="space-y-2 text-sm text-stone-700">
              {session.writing_feedback.map((f, fi) => (
                <li key={`${f.item_id}-${fi}`} className="border-l-2 border-stone-300 pl-3">
                  Task {f.item_id}: {f.score} — {f.feedback}
                </li>
              ))}
            </ul>
          )}
          {error && <p className="text-sm text-red-700">{error}</p>}
          <div className="flex gap-3">
            <Button onClick={handleAssembleRoadmap} disabled={assembling}>
              {assembling ? <Loader2 className="h-4 w-4 animate-spin" /> : "Build roadmap"}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <Button variant="outline" asChild>
              <Link href="/dashboard">Dashboard</Link>
            </Button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f7f4ef] px-6 py-8 text-[#1c1917]">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-stone-500">
              TOEIC-style placement · {session?.section ?? "—"}
            </p>
            <h1 className="font-serif text-2xl">Reading + Writing</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm tabular-nums">{formatTime(left)}</span>
            <LogoutButton />
          </div>
        </div>

        {session?.section === "reading" && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-stone-500">
              <span>
                Page {pageIndex + 1} / {Math.max(readingPages.length, 1)}
              </span>
              <span>
                Answered {readingAnswered} / {readingItems.length}
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-stone-200">
              <div
                className="h-full bg-stone-800 transition-all"
                style={{ width: `${readingProgress}%` }}
              />
            </div>
          </div>
        )}

        {error && <p className="text-sm text-red-700">{error}</p>}

        {session?.section === "reading" && readingPages.length === 0 && !error && (
          <p className="text-sm text-stone-600">
            No reading questions in this session. Refresh the page or start again after the bank is seeded.
          </p>
        )}

        {session?.section === "reading" && currentPage && (
          <section className="space-y-5">
            <p className="text-sm font-medium text-stone-600">{currentPage.label}</p>
            {currentPage.passage && (
              <div className="whitespace-pre-wrap rounded-md bg-white/80 p-4 text-sm leading-relaxed shadow-sm">
                {currentPage.passage}
              </div>
            )}
            <ol className="space-y-6">
              {currentPage.items.map((item, idx) => (
                <li key={`${item.id}-${idx}`} className="space-y-2">
                  <p className="text-base font-medium">
                    <span className="mr-2 text-stone-400">{idx + 1}.</span>
                    {item.stem}
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {(item.options ?? []).map((opt, oi) => (
                      <button
                        key={`${item.id}-opt-${oi}-${opt}`}
                        type="button"
                        className={`rounded-md border px-3 py-2 text-left text-sm ${
                          readingAnswers[item.id] === opt
                            ? "border-stone-900 bg-stone-900 text-white"
                            : "border-stone-300 bg-white"
                        }`}
                        onClick={() =>
                          setReadingAnswers((prev) => {
                            const next = { ...prev, [item.id]: opt };
                            persistReadingDraft(next);
                            return next;
                          })
                        }
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </li>
              ))}
            </ol>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                disabled={busy || pageIndex === 0}
                onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
              >
                Previous page
              </Button>
              <Button onClick={saveReadingPage} disabled={busy}>
                {pageIndex < readingPages.length - 1 ? "Save page & next" : "Save last page"}
              </Button>
              {pageIndex >= readingPages.length - 1 && (
                <Button variant="secondary" onClick={goWriting} disabled={busy}>
                  Go to Writing
                </Button>
              )}
            </div>
          </section>
        )}

        {session?.section === "writing" && currentWriting && (
          <section className="space-y-4">
            <p className="text-sm text-stone-500">
              Writing {writingIndex + 1} / {writingItems.length} ·{" "}
              {currentWriting.toeic_part?.toUpperCase()}
            </p>
            {writingPassage && (
              <div className="whitespace-pre-wrap rounded-md bg-white/80 p-4 text-sm leading-relaxed">
                {writingPassage}
              </div>
            )}
            <p className="text-lg">{currentWriting.stem}</p>
            {currentWriting.prompt_words && (
              <p className="rounded-md border border-stone-200 bg-stone-50 px-3 py-2 font-medium tracking-wide">
                Words: {currentWriting.prompt_words.join(" / ")}
              </p>
            )}
            <textarea
              className="min-h-40 w-full rounded-md border border-stone-300 bg-white p-3 text-sm"
              value={writingText}
              onChange={(e) => {
                const text = e.target.value;
                setWritingText(text);
                if (currentWriting) persistWritingDraft(currentWriting.id, text);
              }}
              placeholder="Write your response…"
            />
            <div className="flex flex-wrap gap-2">
              <Button onClick={saveWriting} disabled={busy || !writingText.trim()}>
                Submit response
              </Button>
              {writingIndex >= writingItems.length - 1 && (
                <Button variant="outline" onClick={finish} disabled={busy}>
                  Finish placement
                </Button>
              )}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
