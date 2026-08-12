"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Clock3, Flag, Loader2, LogOut } from "lucide-react";
import PlacementComplete from "@/components/onboarding/PlacementComplete";
import PlacementNavigator from "@/components/onboarding/placement/PlacementNavigator";
import {
  buildReadingPages,
  clearDraft,
  countWords,
  firstIncompleteReadingPage,
  firstIncompleteWritingIndex,
  formatTime,
  loadDraft,
  OPTION_LETTERS,
  optionClass,
  pageIndexForItem,
  primaryBtnClass,
  saveDraft,
  savedAnswersToMap,
  secondaryBtnClass,
} from "@/components/onboarding/placement/helpers";
import { cn } from "@/lib/utils";
import { fetchOnboardingStatus } from "@/lib/onboarding-status";
import { logout } from "@/lib/api";
import {
  advancePlacementSection,
  completePlacementSession,
  fetchPlacementAccessStatus,
  getCurrentPlacementSession,
  startPlacementSession,
  submitReadingAnswers,
  submitWritingAnswer,
  type PlacementSession,
} from "@/lib/placement";
import { assembleRoadmap } from "@/lib/roadmap";

type Gate = "directions" | "test" | "review";

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

function taskBriefLines(brief: Record<string, unknown> | null | undefined) {
  if (!brief) return [];
  const lines: string[] = [];
  for (const [key, value] of Object.entries(brief)) {
    if (value == null || value === "") continue;
    if (typeof value === "string" || typeof value === "number") {
      lines.push(`${key.replace(/_/g, " ")}: ${value}`);
    } else if (Array.isArray(value)) {
      lines.push(`${key.replace(/_/g, " ")}: ${value.join(", ")}`);
    }
  }
  return lines;
}

export default function PlacementPage() {
  const router = useRouter();
  const [session, setSession] = useState<PlacementSession | null>(null);
  const [readingAnswers, setReadingAnswers] = useState<Record<number, string>>(
    {},
  );
  const [markedIds, setMarkedIds] = useState<Set<number>>(new Set());
  const [pageIndex, setPageIndex] = useState(0);
  const [writingIndex, setWritingIndex] = useState(0);
  const [writingText, setWritingText] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [assembling, setAssembling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gate, setGate] = useState<Gate>("directions");
  const [activeItemId, setActiveItemId] = useState<number | null>(null);
  const [leaveOpen, setLeaveOpen] = useState(false);
  const loadStarted = useRef(false);
  const timedOutRef = useRef(false);
  const answersRef = useRef(readingAnswers);
  const writingTextRef = useRef(writingText);
  const sessionRef = useRef(session);
  const pageIndexRef = useRef(pageIndex);
  const writingIndexRef = useRef(writingIndex);
  const busyRef = useRef(busy);

  const left = useCountdown(session?.section_ends_at);
  const timerUrgent = left != null && left <= 5 * 60;

  useEffect(() => {
    answersRef.current = readingAnswers;
  }, [readingAnswers]);
  useEffect(() => {
    writingTextRef.current = writingText;
  }, [writingText]);
  useEffect(() => {
    sessionRef.current = session;
  }, [session]);
  useEffect(() => {
    pageIndexRef.current = pageIndex;
  }, [pageIndex]);
  useEffect(() => {
    writingIndexRef.current = writingIndex;
  }, [writingIndex]);
  useEffect(() => {
    busyRef.current = busy;
  }, [busy]);

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
      ? (passages[String(currentWriting.passage_id)]?.body ?? null)
      : null;
  const writingMedia =
    currentWriting?.media_url ??
    (currentWriting?.passage_id != null
      ? (passages[String(currentWriting.passage_id)]?.media_url ?? null)
      : null);

  const readingUnanswered = useMemo(
    () =>
      readingPages
        .flatMap((p) => p.items)
        .filter((it) => !readingAnswers[it.id]),
    [readingPages, readingAnswers],
  );
  const readingMarked = useMemo(
    () =>
      readingPages
        .flatMap((p) => p.items)
        .filter((it) => markedIds.has(it.id)),
    [readingPages, markedIds],
  );
  const readingIdSet = useMemo(
    () => new Set(readingPages.flatMap((p) => p.items.map((it) => it.id))),
    [readingPages],
  );
  const readingAnswered = useMemo(
    () =>
      Object.entries(readingAnswers).filter(
        ([id, value]) => readingIdSet.has(Number(id)) && Boolean(value),
      ).length,
    [readingAnswers, readingIdSet],
  );
  const readingTotal = readingIdSet.size;
  const readingProgress =
    readingTotal > 0
      ? Math.round((readingAnswered / readingTotal) * 100)
      : 0;
  const writingAnsweredIds = useMemo(() => {
    const ids = new Set<number>();
    if (!session) return ids;
    const serverMap = savedAnswersToMap(session.saved_answers);
    const draft = loadDraft(session.attempt_id);
    for (const item of writingItems) {
      if (
        serverMap[item.id] ||
        draft.writingTextById?.[String(item.id)] ||
        (currentWriting?.id === item.id && writingText.trim())
      ) {
        ids.add(item.id);
      }
    }
    return ids;
  }, [session, writingItems, currentWriting?.id, writingText]);

  const wordCount = countWords(writingText);
  const briefLines = taskBriefLines(currentWriting?.task_brief);
  const splitLayout = Boolean(currentPage?.passage);

  function persistMarked(next: Set<number>) {
    if (!session) return;
    const draft = loadDraft(session.attempt_id);
    saveDraft(session.attempt_id, {
      ...draft,
      markedIds: Array.from(next),
    });
  }

  function hydrateFromSession(
    next: PlacementSession,
    opts?: {
      keepPage?: boolean;
      preserveGate?: boolean;
      writingIndex?: number;
    },
  ) {
    const prevSection = sessionRef.current?.section;
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
    const pages = buildReadingPages(
      next.form?.reading_items ?? [],
      next.form?.passages ?? {},
    );
    const readingIds = new Set(
      pages.flatMap((p) => p.items.map((it) => it.id)),
    );
    const filteredReading: Record<number, string> = {};
    for (const [id, value] of Object.entries(mergedReading)) {
      const numId = Number(id);
      if (readingIds.has(numId) && value) filteredReading[numId] = value;
    }
    setReadingAnswers(filteredReading);
    setMarkedIds(
      new Set((draft.markedIds ?? []).filter((id) => readingIds.has(id))),
    );

    const wItems = next.form?.writing_items ?? [];
    const sectionChanged = prevSection != null && prevSection !== next.section;

    if (next.section === "writing") {
      const maxIdx = Math.max(0, wItems.length - 1);
      const wIdx =
        opts?.writingIndex != null
          ? Math.min(Math.max(0, opts.writingIndex), maxIdx)
          : firstIncompleteWritingIndex(wItems, serverMap);
      setWritingIndex(wIdx);
      const wId = wItems[wIdx]?.id;
      const fromServer = wId != null ? serverMap[wId] : "";
      const fromDraft =
        wId != null ? (draft.writingTextById?.[String(wId)] ?? "") : "";
      setWritingText(fromDraft || fromServer || "");
      setPageIndex(Math.max(0, pages.length - 1));
      if (!opts?.preserveGate && (sectionChanged || prevSection == null)) {
        setGate("directions");
        timedOutRef.current = false;
      }
    } else if (!opts?.keepPage) {
      const idx = firstIncompleteReadingPage(pages, mergedReading);
      setPageIndex(idx);
      setActiveItemId(pages[idx]?.items[0]?.id ?? null);
      setWritingIndex(0);
      setWritingText("");
      if (!opts?.preserveGate && (sectionChanged || prevSection == null)) {
        setGate("directions");
        timedOutRef.current = false;
      }
    }
  }

  function persistReadingDraft(nextAnswers: Record<number, string>) {
    if (!session) return;
    const draft = loadDraft(session.attempt_id);
    const reading: Record<string, string> = {};
    for (const [id, val] of Object.entries(nextAnswers)) {
      reading[String(id)] = val;
    }
    saveDraft(session.attempt_id, {
      ...draft,
      reading,
      markedIds: Array.from(markedIds),
    });
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
      markedIds: Array.from(markedIds),
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
        setError(
          err instanceof Error ? err.message : "Failed to load placement",
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  useEffect(() => {
    if (gate !== "test" || session?.done) return;
    function onBeforeUnload(e: BeforeUnloadEvent) {
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [gate, session?.done]);

  async function flushReadingAnswers(
    answers: Record<number, string>,
    attemptId: number,
  ) {
    const payload = Object.entries(answers)
      .filter(([, v]) => Boolean(v))
      .map(([id, given_answer]) => ({
        item_id: Number(id),
        given_answer,
      }));
    if (payload.length === 0) return getCurrentPlacementSession();
    return submitReadingAnswers(attemptId, payload);
  }

  const handleTimeUp = useCallback(async () => {
    if (timedOutRef.current || busyRef.current) return;
    const current = sessionRef.current;
    if (!current || current.done) return;
    timedOutRef.current = true;
    setBusy(true);
    setError(null);
    setGate("test");
    try {
      if (current.section === "reading") {
        const next =
          (await flushReadingAnswers(
            answersRef.current,
            current.attempt_id,
          )) ?? current;
        const advanced = await advancePlacementSection(
          next?.attempt_id ?? current.attempt_id,
        );
        hydrateFromSession(advanced);
        setError("Time is up for Reading. Moving to Writing.");
      } else if (current.section === "writing") {
        await flushAllWritingAnswers(current.attempt_id);
        const done = await completePlacementSession(current.attempt_id);
        clearDraft(done.attempt_id);
        setSession(done);
      }
    } catch (err) {
      timedOutRef.current = false;
      setError(
        err instanceof Error ? err.message : "Could not auto-submit on time up",
      );
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (left === 0 && session && !session.done && gate === "test") {
      void handleTimeUp();
    }
  }, [left, session, gate, handleTimeUp]);

  async function saveReadingPage() {
    if (!session || !currentPage) return;
    const missing = currentPage.items.filter((it) => !readingAnswers[it.id]);
    if (missing.length > 0) {
      setError(`Answer all ${missing.length} question(s) on this page`);
      return;
    }
    const currentIdx = pageIndex;
    setBusy(true);
    setError(null);
    try {
      const payload = currentPage.items.map((it) => ({
        item_id: it.id,
        given_answer: readingAnswers[it.id],
      }));
      const next = await submitReadingAnswers(session.attempt_id, payload);
      hydrateFromSession(next, { keepPage: true });
      const pages = buildReadingPages(
        next.form?.reading_items ?? [],
        next.form?.passages ?? {},
      );
      const target =
        currentIdx < pages.length - 1
          ? currentIdx + 1
          : Math.max(0, pages.length - 1);
      setPageIndex(target);
      setActiveItemId(pages[target]?.items[0]?.id ?? null);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submit failed");
    } finally {
      setBusy(false);
    }
  }

  async function confirmLeaveReading() {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const next =
        (await flushReadingAnswers(readingAnswers, session.attempt_id)) ??
        session;
      const advanced = await advancePlacementSection(next.attempt_id);
      hydrateFromSession(advanced);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Cannot advance yet — finish Reading",
      );
      setGate("test");
    } finally {
      setBusy(false);
    }
  }

  async function flushAllWritingAnswers(attemptId: number) {
    const current = sessionRef.current;
    const items = current?.form?.writing_items ?? [];
    const draft = loadDraft(attemptId);
    const texts: Record<string, string> = {
      ...(draft.writingTextById ?? {}),
    };
    const liveItem = items[writingIndexRef.current];
    if (liveItem) {
      texts[String(liveItem.id)] = writingTextRef.current;
    }
    saveDraft(attemptId, {
      ...draft,
      writingTextById: texts,
      markedIds: draft.markedIds,
    });
    await Promise.all(
      items.map((item) =>
        submitWritingAnswer(attemptId, {
          item_id: item.id,
          text: texts[String(item.id)] ?? "",
        }),
      ),
    );
  }

  function goToWritingIndex(nextIdx: number) {
    if (!session || busy) return;
    if (nextIdx < 0 || nextIdx >= writingItems.length) return;
    if (nextIdx === writingIndex) return;
    if (currentWriting) {
      persistWritingDraft(currentWriting.id, writingText);
    }
    const draft = loadDraft(session.attempt_id);
    const item = writingItems[nextIdx];
    setWritingIndex(nextIdx);
    setWritingText(
      item ? (draft.writingTextById?.[String(item.id)] ?? "") : "",
    );
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function finish() {
    if (!session || busy) return;
    setBusy(true);
    setError(null);
    try {
      await flushAllWritingAnswers(session.attempt_id);
      const next = await completePlacementSession(session.attempt_id);
      clearDraft(next.attempt_id);
      setSession(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Complete failed");
      setGate("test");
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
      setError(
        err instanceof Error ? err.message : "Failed to assemble roadmap",
      );
    } finally {
      setAssembling(false);
    }
  }

  function jumpToItem(itemId: number) {
    const idx = pageIndexForItem(readingPages, itemId);
    setPageIndex(idx);
    setActiveItemId(itemId);
    setGate("test");
    window.setTimeout(() => {
      document
        .getElementById(`placement-q-${itemId}`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  }

  // Keep navigator focused when paging with Previous/Next.
  useEffect(() => {
    if (gate !== "test" || session?.section !== "reading") return;
    const firstOnPage = currentPage?.items[0]?.id;
    if (firstOnPage == null) return;
    if (
      activeItemId != null &&
      currentPage.items.some((it) => it.id === activeItemId)
    ) {
      return;
    }
    setActiveItemId(firstOnPage);
  }, [pageIndex, gate, session?.section, currentPage, activeItemId]);

  function toggleMark(itemId: number) {
    setMarkedIds((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) next.delete(itemId);
      else next.add(itemId);
      persistMarked(next);
      return next;
    });
  }

  async function confirmLeaveTest() {
    setLeaveOpen(false);
    await logout();
  }

  if (loading) {
    return (
      <main className="relative flex min-h-screen items-center justify-center overflow-x-hidden bg-[#FFF5EB] text-[#1F1B15]">
        <div className="flex items-center gap-2 text-[0.875rem] text-[#8A8178]">
          <Loader2 className="h-5 w-5 animate-spin text-[#E85D04]" aria-hidden />
          Loading placement…
        </div>
      </main>
    );
  }

  if (session?.done) {
    return (
      <PlacementComplete
        session={session}
        error={error}
        assembling={assembling}
        onAssemble={handleAssembleRoadmap}
      />
    );
  }

  const sectionLabel =
    session?.section === "writing" ? "Writing" : "Reading";

  return (
    <main className="relative min-h-screen bg-[#FFF5EB] px-4 py-6 text-[#1F1B15] sm:px-6 md:px-8">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 overflow-x-clip"
        style={{
          background:
            "radial-gradient(ellipse 55% 40% at 10% 6%, rgba(232, 93, 4, 0.12), transparent 58%), radial-gradient(ellipse 45% 35% at 92% 18%, rgba(13, 148, 136, 0.1), transparent 55%)",
        }}
      />

      <div className="relative mx-auto max-w-6xl space-y-4">
        <header className="flex flex-wrap items-center justify-between gap-3 rounded-[1rem] bg-white/90 px-4 py-3.5 shadow-[0_10px_32px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06 backdrop-blur-sm sm:px-5">
          <div className="min-w-0">
            <p className="text-[0.8125rem] font-medium text-[#8A8178]">
              TOEIC-style placement · {sectionLabel}
            </p>
            <h1 className="mt-0.5 text-[1.25rem] font-semibold tracking-tight text-[#1F1B15]">
              {sectionLabel} section
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "inline-flex min-h-11 items-center gap-1.5 rounded-[1rem] px-3.5 text-[0.875rem] font-semibold tabular-nums ring-1",
                timerUrgent
                  ? "bg-[#FFE4E6] text-[#BE123C] ring-[#BE123C]/25"
                  : "bg-[#FFFAF5] text-[#115E59] ring-[#E9D7C9]",
              )}
              aria-live="polite"
              aria-label={`Time remaining ${formatTime(left)}`}
            >
              <Clock3 className="h-4 w-4" aria-hidden />
              {formatTime(left)}
            </span>
            <button
              type="button"
              onClick={() => setLeaveOpen(true)}
              disabled={busy}
              className="inline-flex min-h-11 items-center gap-1.5 rounded-[1rem] px-3 text-[0.8125rem] font-semibold text-[#8A8178] transition-colors hover:bg-[#FFE4E6] hover:text-[#BE123C] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#BE123C] disabled:pointer-events-none disabled:opacity-50"
            >
              <LogOut className="h-3.5 w-3.5" aria-hidden />
              Leave
            </button>
          </div>
        </header>

        {session?.section === "reading" && gate === "test" ? (
          <div className="space-y-2 px-1">
            <div className="flex justify-between text-[0.8125rem] font-medium text-[#8A8178]">
              <span>
                Page {pageIndex + 1} / {Math.max(readingPages.length, 1)}
              </span>
              <span>
                Answered {readingAnswered} / {readingTotal}
              </span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-[#E9D7C9]"
              role="progressbar"
              aria-valuenow={readingProgress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Reading progress"
            >
              <div
                className="h-full rounded-full bg-[#E85D04] transition-[width] duration-300 ease-out"
                style={{ width: `${readingProgress}%` }}
              />
            </div>
          </div>
        ) : null}

        {error ? (
          <div
            className="rounded-[1rem] bg-[#FFE4E6] px-4 py-3 text-[0.875rem] text-[#BE123C] ring-1 ring-[#BE123C]/25"
            role="alert"
          >
            {error}
          </div>
        ) : null}

        {gate === "directions" ? (
          <section className="mx-auto max-w-2xl rounded-[1rem] bg-white p-6 shadow-[0_18px_50px_rgba(31,27,21,0.08)] ring-1 ring-[#1F1B15]/06 sm:p-8">
            <h2 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]">
              {session?.section === "writing"
                ? "Writing directions"
                : "Reading directions"}
            </h2>
            {session?.section === "writing" ? (
              <ul className="mt-4 list-disc space-y-2 pl-5 text-[0.9375rem] leading-relaxed text-[#6B6258]">
                <li>You have about 58 minutes for all writing tasks.</li>
                <li>Read each prompt carefully. Use the word counter.</li>
                <li>Submit each response before moving on.</li>
                <li>When time ends, your work is submitted automatically.</li>
              </ul>
            ) : (
              <ul className="mt-4 list-disc space-y-2 pl-5 text-[0.9375rem] leading-relaxed text-[#6B6258]">
                <li>You have about 75 minutes for the full Reading section.</li>
                <li>Part 5: incomplete sentences. Parts 6–7: passage + questions.</li>
                <li>Use the question grid to jump. Flag items to review later.</li>
                <li>Choose one answer (A–D) per question. You can change answers.</li>
                <li>When time ends, answered items are submitted and Writing begins.</li>
              </ul>
            )}
            <button
              type="button"
              className={primaryBtnClass("mt-7")}
              onClick={() => setGate("test")}
            >
              Begin {sectionLabel.toLowerCase()}
            </button>
          </section>
        ) : null}

        {gate === "review" && session?.section === "reading" ? (
          <section className="mx-auto max-w-2xl rounded-[1rem] bg-white p-6 shadow-[0_18px_50px_rgba(31,27,21,0.08)] ring-1 ring-[#1F1B15]/06 sm:p-8">
            <h2 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]">
              Review before Writing
            </h2>
            <p className="mt-2 text-[0.9375rem] text-[#6B6258]">
              {readingUnanswered.length === 0
                ? "All reading questions are answered."
                : `You still have ${readingUnanswered.length} unanswered question(s).`}
              {readingMarked.length > 0
                ? ` ${readingMarked.length} marked for review.`
                : ""}
            </p>
            {readingUnanswered.length > 0 ? (
              <div className="mt-4 flex flex-wrap gap-1.5">
                {readingUnanswered.slice(0, 40).map((it) => (
                  <button
                    key={it.id}
                    type="button"
                    onClick={() => jumpToItem(it.id)}
                    className="inline-flex h-9 min-w-9 items-center justify-center rounded-[1rem] bg-[#FFFAF5] px-2 text-[0.75rem] font-semibold text-[#8A8178] ring-1 ring-[#E9D7C9]"
                  >
                    {it.globalIndex}
                  </button>
                ))}
              </div>
            ) : null}
            <div className="mt-7 flex flex-wrap gap-2">
              <button
                type="button"
                className={secondaryBtnClass()}
                disabled={busy}
                onClick={() => setGate("test")}
              >
                Back to questions
              </button>
              <button
                type="button"
                disabled={busy}
                aria-busy={busy}
                className={primaryBtnClass()}
                onClick={() => void confirmLeaveReading()}
              >
                {busy ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                ) : null}
                {readingUnanswered.length > 0
                  ? "Submit Reading anyway"
                  : "Go to Writing"}
              </button>
            </div>
          </section>
        ) : null}

        {gate === "review" && session?.section === "writing" ? (
          <section
            className="relative mx-auto max-w-2xl rounded-[1rem] bg-white p-6 shadow-[0_18px_50px_rgba(31,27,21,0.08)] ring-1 ring-[#1F1B15]/06 sm:p-8"
            aria-busy={busy}
          >
            <h2 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]">
              Finish placement?
            </h2>
            <p className="mt-2 text-[0.9375rem] text-[#6B6258]">
              This ends Writing, grades all responses once, then calculates your
              starting level. It may take a short moment.
            </p>
            <div className="mt-7 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy}
                className={secondaryBtnClass()}
                onClick={() => setGate("test")}
              >
                Keep writing
              </button>
              <button
                type="button"
                disabled={busy}
                aria-busy={busy}
                className={primaryBtnClass()}
                onClick={() => void finish()}
              >
                {busy ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                ) : null}
                {busy ? "Grading writing…" : "Finish placement"}
              </button>
            </div>
            {busy ? (
              <div
                className="absolute inset-0 z-10 cursor-wait rounded-[1rem] bg-white/50"
                aria-hidden
              />
            ) : null}
          </section>
        ) : null}

        {gate === "test" && session?.section === "reading" ? (
          <div className="grid gap-2 lg:grid-cols-[minmax(0,1fr)_14rem]">
            <div className="min-w-0 space-y-4">
              {readingPages.length === 0 && !error ? (
                <p className="text-[0.875rem] text-[#8A8178]">
                  No reading questions in this session.
                </p>
              ) : null}

              {currentPage ? (
                <section className="rounded-[1rem] bg-white p-4 shadow-[0_18px_50px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06 sm:p-6">
                  <p className="text-[0.875rem] font-semibold text-[#6B6258]">
                    {currentPage.label}
                  </p>

                  <div
                    className={cn(
                      "mt-4 gap-5",
                      splitLayout && "lg:grid lg:grid-cols-2 lg:items-start",
                    )}
                  >
                    {currentPage.passage ? (
                      <div className="space-y-3 lg:sticky lg:top-4 lg:max-h-[70vh] lg:overflow-y-auto">
                        {currentPage.mediaUrl ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={currentPage.mediaUrl}
                            alt=""
                            className="max-h-56 w-full rounded-[1rem] object-contain ring-1 ring-[#E9D7C9]"
                          />
                        ) : null}
                        <div className="whitespace-pre-wrap rounded-[1rem] bg-[#FFFAF5] px-4 py-4 text-[0.9375rem] leading-relaxed text-[#1F1B15] ring-1 ring-[#E9D7C9]">
                          {currentPage.passage}
                        </div>
                      </div>
                    ) : null}

                    <ol className="space-y-5">
                      {currentPage.items.map((item) => (
                        <li
                          key={item.id}
                          id={`placement-q-${item.id}`}
                          className={cn(
                            "space-y-2.5 rounded-[1rem] p-1",
                            activeItemId === item.id && "ring-2 ring-[#E85D04]/30",
                          )}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-[0.9375rem] font-semibold text-[#1F1B15]">
                              <span className="mr-2 font-medium text-[#A89F94]">
                                Q{item.globalIndex}.
                              </span>
                              {item.stem}
                            </p>
                            <button
                              type="button"
                              onClick={() => toggleMark(item.id)}
                              aria-pressed={markedIds.has(item.id)}
                              aria-label={
                                markedIds.has(item.id)
                                  ? "Unmark for review"
                                  : "Mark for review"
                              }
                              className={cn(
                                "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-[1rem] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0D9488]",
                                markedIds.has(item.id)
                                  ? "bg-[#CCFBF1] text-[#0D9488]"
                                  : "text-[#A89F94] hover:bg-[#FFFAF5] hover:text-[#0D9488]",
                              )}
                            >
                              <Flag className="h-4 w-4" aria-hidden />
                            </button>
                          </div>
                          <div className="grid gap-2 sm:grid-cols-2">
                            {(item.options ?? []).map((opt, oi) => {
                              const letter = OPTION_LETTERS[oi] ?? String(oi + 1);
                              return (
                                <button
                                  key={`${item.id}-opt-${oi}-${opt}`}
                                  type="button"
                                  className={optionClass(
                                    readingAnswers[item.id] === opt,
                                  )}
                                  onClick={() => {
                                    setActiveItemId(item.id);
                                    setReadingAnswers((prev) => {
                                      const next = { ...prev, [item.id]: opt };
                                      persistReadingDraft(next);
                                      return next;
                                    });
                                  }}
                                >
                                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-white/80 text-[0.75rem] font-semibold text-[#9A3412] ring-1 ring-[#E9D7C9]">
                                    {letter}
                                  </span>
                                  <span>{opt}</span>
                                </button>
                              );
                            })}
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy || pageIndex === 0}
                      onClick={() => {
                        const prev = Math.max(0, pageIndex - 1);
                        setPageIndex(prev);
                        setActiveItemId(
                          readingPages[prev]?.items[0]?.id ?? null,
                        );
                      }}
                      className={secondaryBtnClass()}
                    >
                      Previous page
                    </button>
                    <button
                      type="button"
                      onClick={() => void saveReadingPage()}
                      disabled={busy}
                      aria-busy={busy}
                      className={primaryBtnClass()}
                    >
                      {busy ? (
                        <Loader2
                          className="mr-2 h-4 w-4 animate-spin"
                          aria-hidden
                        />
                      ) : null}
                      {pageIndex < readingPages.length - 1
                        ? "Next page"
                        : "Save page"}
                    </button>
                    {pageIndex >= readingPages.length - 1 ? (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => setGate("review")}
                        className={secondaryBtnClass(
                          "bg-[#CCFBF1] text-[#115E59] ring-[#0D9488]/25 hover:bg-[#99F6E4]",
                        )}
                      >
                        Review &amp; go to Writing
                      </button>
                    ) : null}
                  </div>
                </section>
              ) : null}
            </div>

            <PlacementNavigator
              pages={readingPages}
              answers={readingAnswers}
              markedIds={markedIds}
              activeItemId={activeItemId}
              onSelect={jumpToItem}
            />
          </div>
        ) : null}

        {gate === "test" && session?.section === "writing" && currentWriting ? (
          <section className="mx-auto max-w-3xl space-y-4 rounded-[1rem] bg-white p-5 shadow-[0_18px_50px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06 sm:p-7">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-[0.8125rem] font-medium text-[#8A8178]">
                Writing {writingIndex + 1} / {writingItems.length} ·{" "}
                {currentWriting.toeic_part?.toUpperCase()}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {writingItems.map((item, idx) => {
                  const hasText = writingAnsweredIds.has(item.id);
                  const active = idx === writingIndex;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      disabled={busy}
                      onClick={() => goToWritingIndex(idx)}
                      aria-label={`Writing task ${idx + 1}${hasText ? ", saved" : ""}`}
                      aria-current={active ? "true" : undefined}
                      className={cn(
                        "inline-flex h-8 min-w-8 items-center justify-center rounded-lg px-2 text-[0.75rem] font-semibold tabular-nums transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]",
                        active
                          ? "bg-[#E85D04] text-white"
                          : hasText
                            ? "bg-[#FFE8D6] text-[#9A3412]"
                            : "bg-[#FFFAF5] text-[#8A8178] ring-1 ring-inset ring-[#E9D7C9]",
                      )}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>
            </div>
            {writingMedia ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={writingMedia}
                alt=""
                className="max-h-72 w-full rounded-[1rem] object-contain ring-1 ring-[#E9D7C9]"
              />
            ) : null}
            {writingPassage ? (
              <div className="whitespace-pre-wrap rounded-[1rem] bg-[#FFFAF5] px-4 py-4 text-[0.9375rem] leading-relaxed text-[#1F1B15] ring-1 ring-[#E9D7C9]">
                {writingPassage}
              </div>
            ) : null}
            <p className="text-[1.25rem] font-semibold tracking-tight text-[#1F1B15]">
              {currentWriting.stem}
            </p>
            {currentWriting.prompt_words ? (
              <p className="rounded-[1rem] bg-[#CCFBF1]/60 px-4 py-2.5 text-[0.875rem] font-semibold tracking-wide text-[#115E59] ring-1 ring-[#0D9488]/20">
                Words: {currentWriting.prompt_words.join(" / ")}
              </p>
            ) : null}
            {briefLines.length > 0 ? (
              <ul className="rounded-[1rem] bg-[#FFFAF5] px-4 py-3 text-[0.8125rem] leading-relaxed text-[#6B6258] ring-1 ring-[#E9D7C9]">
                {briefLines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            ) : null}
            <textarea
              className="min-h-40 w-full resize-y rounded-[1rem] border border-[#E9D7C9] bg-[#FFFAF5] p-4 text-[0.9375rem] leading-relaxed text-[#1F1B15] placeholder:text-[#A89F94] focus-visible:border-[#E85D04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]/25"
              value={writingText}
              onChange={(e) => {
                const text = e.target.value;
                setWritingText(text);
                persistWritingDraft(currentWriting.id, text);
              }}
              placeholder="Write your response…"
            />
            <p className="text-[0.8125rem] font-medium text-[#8A8178]">
              Word count: {wordCount}. Answers are saved on this device until
              you finish.
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => goToWritingIndex(writingIndex - 1)}
                disabled={busy || writingIndex <= 0}
                className={secondaryBtnClass()}
              >
                Previous
              </button>
              {writingIndex < writingItems.length - 1 ? (
                <button
                  type="button"
                  onClick={() => goToWritingIndex(writingIndex + 1)}
                  disabled={busy}
                  className={primaryBtnClass()}
                >
                  Next
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setGate("review")}
                  disabled={busy}
                  className={primaryBtnClass()}
                >
                  Review &amp; finish
                </button>
              )}
            </div>
          </section>
        ) : null}
      </div>

      {leaveOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button
            type="button"
            aria-label="Cancel leave"
            className="absolute inset-0 bg-[#1F1B15]/40"
            onClick={() => setLeaveOpen(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="leave-test-title"
            className="relative z-10 w-full max-w-md rounded-[1rem] bg-white p-6 shadow-[0_24px_60px_rgba(31,27,21,0.18)] ring-1 ring-[#1F1B15]/06"
          >
            <h2
              id="leave-test-title"
              className="text-[1.25rem] font-semibold text-[#1F1B15]"
            >
              Leave the test?
            </h2>
            <p className="mt-2 text-[0.9375rem] text-[#6B6258]">
              Your drafted answers stay on this device, but leaving signs you
              out. You can resume an in-progress attempt when you sign back in.
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className={secondaryBtnClass()}
                onClick={() => setLeaveOpen(false)}
              >
                Stay
              </button>
              <button
                type="button"
                className="inline-flex h-11 items-center rounded-[1rem] bg-[#BE123C] px-5 text-[0.875rem] font-semibold text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#BE123C]"
                onClick={() => void confirmLeaveTest()}
              >
                Leave &amp; sign out
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
