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
  fetchRetakeStatus,
  getCurrentPlacementSession,
  startPlacementSession,
  submitReadingAnswers,
  submitWritingAnswer,
  type PlacementFormItem,
  type PlacementSession,
} from "@/lib/placement";
import { assembleRoadmap } from "@/lib/roadmap";

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

export default function PlacementPage() {
  const router = useRouter();
  const [session, setSession] = useState<PlacementSession | null>(null);
  const [readingAnswers, setReadingAnswers] = useState<Record<number, string>>({});
  const [readingIndex, setReadingIndex] = useState(0);
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
  const currentReading = readingItems[readingIndex] as PlacementFormItem | undefined;
  const currentWriting = writingItems[writingIndex] as PlacementFormItem | undefined;

  const passageBody = useMemo(() => {
    const item = session?.section === "writing" ? currentWriting : currentReading;
    if (!item?.passage_id) return null;
    return passages[String(item.passage_id)]?.body ?? null;
  }, [session?.section, currentReading, currentWriting, passages]);

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
        const retake = await fetchRetakeStatus().catch(() => null);
        const canEnter =
          !status.placement_done ||
          Boolean(retake?.allowed) ||
          Boolean(retake?.has_in_progress);
        if (!canEnter) {
          router.replace("/dashboard");
          return;
        }
        let next = await getCurrentPlacementSession();
        if (!next) next = await startPlacementSession();
        setSession(next);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load placement");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  async function saveCurrentReadingAnswer() {
    if (!session || !currentReading) return;
    const given = readingAnswers[currentReading.id] ?? "";
    if (!given) {
      setError("Select an answer first");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await submitReadingAnswers(session.attempt_id, [
        { item_id: currentReading.id, given_answer: given },
      ]);
      setSession(next);
      if (readingIndex < readingItems.length - 1) {
        setReadingIndex((i) => i + 1);
      }
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
      setSession(next);
      setWritingIndex(0);
      setWritingText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot advance yet");
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
      setSession(next);
      if (writingIndex < writingItems.length - 1) {
        setWritingIndex((i) => i + 1);
        setWritingText("");
      }
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
              {session.writing_feedback.map((f) => (
                <li key={f.item_id} className="border-l-2 border-stone-300 pl-3">
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

        {error && <p className="text-sm text-red-700">{error}</p>}

        {session?.section === "reading" && currentReading && (
          <section className="space-y-4">
            <p className="text-sm text-stone-500">
              Reading {readingIndex + 1} / {readingItems.length} · {currentReading.toeic_part}
            </p>
            {passageBody && (
              <div className="whitespace-pre-wrap rounded-md bg-white/70 p-4 text-sm leading-relaxed">
                {passageBody}
              </div>
            )}
            <p className="text-lg">{currentReading.stem}</p>
            <div className="grid gap-2">
              {(currentReading.options ?? []).map((opt) => (
                <button
                  key={opt}
                  type="button"
                  className={`rounded-md border px-3 py-2 text-left text-sm ${
                    readingAnswers[currentReading.id] === opt
                      ? "border-stone-900 bg-stone-900 text-white"
                      : "border-stone-300 bg-white"
                  }`}
                  onClick={() =>
                    setReadingAnswers((prev) => ({ ...prev, [currentReading.id]: opt }))
                  }
                >
                  {opt}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={saveCurrentReadingAnswer} disabled={busy}>
                Save & next
              </Button>
              {readingIndex >= readingItems.length - 1 && (
                <Button variant="outline" onClick={goWriting} disabled={busy}>
                  Go to Writing
                </Button>
              )}
            </div>
          </section>
        )}

        {session?.section === "writing" && currentWriting && (
          <section className="space-y-4">
            <p className="text-sm text-stone-500">
              Writing {writingIndex + 1} / {writingItems.length} · {currentWriting.toeic_part}
            </p>
            {currentWriting.media_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={currentWriting.media_url}
                alt="Writing prompt"
                className="max-h-64 rounded-md border border-stone-200 object-contain"
              />
            )}
            {passageBody && (
              <div className="whitespace-pre-wrap rounded-md bg-white/70 p-4 text-sm leading-relaxed">
                {passageBody}
              </div>
            )}
            <p className="text-lg">{currentWriting.stem}</p>
            {currentWriting.prompt_words && (
              <p className="text-sm text-stone-600">
                Words: {currentWriting.prompt_words.join(" / ")}
              </p>
            )}
            <textarea
              className="min-h-40 w-full rounded-md border border-stone-300 bg-white p-3 text-sm"
              value={writingText}
              onChange={(e) => setWritingText(e.target.value)}
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
