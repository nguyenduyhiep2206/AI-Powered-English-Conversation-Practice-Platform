"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import LogoutButton from "@/components/ui/LogoutButton";
import { fetchOnboardingStatus } from "@/lib/onboarding-status";
import {
  fetchRetakeStatus,
  getCurrentPlacementSession,
  startPlacementSession,
  submitPlacementAnswer,
  type PlacementProgress,
  type PlacementQuestion,
  type PlacementSession,
} from "@/lib/placement";
import { assembleRoadmap } from "@/lib/roadmap";

export default function PlacementPage() {
  const router = useRouter();
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [question, setQuestion] = useState<PlacementQuestion | null>(null);
  const [progress, setProgress] = useState<PlacementProgress | null>(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [assembling, setAssembling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PlacementSession | null>(null);
  const loadStarted = useRef(false);

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

        let session = await getCurrentPlacementSession();
        if (!session) {
          session = await startPlacementSession();
        }
        if (session.done) {
          setResult(session);
          return;
        }
        setAttemptId(session.attempt_id);
        setQuestion(session.question ?? null);
        setProgress(session.progress ?? null);
        setAnswer("");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load placement");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  async function handleSubmitAnswer() {
    if (!attemptId || !question || !answer.trim()) {
      setError("Please answer before continuing");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const session = await submitPlacementAnswer(attemptId, {
        question_id: question.id,
        answer: answer.trim(),
      });
      if (session.done) {
        setResult(session);
        router.refresh();
        return;
      }
      setAttemptId(session.attempt_id);
      setQuestion(session.question ?? null);
      setProgress(session.progress ?? null);
      setAnswer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit answer");
    } finally {
      setSubmitting(false);
    }
  }

  async function goToRoadmap() {
    setAssembling(true);
    setError(null);
    try {
      await assembleRoadmap();
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create your learning path",
      );
    } finally {
      setAssembling(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const asked = progress?.asked ?? 0;
  const maxQ = progress?.max_questions ?? 15;
  const minQ = progress?.min_questions ?? 6;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex items-center justify-between px-6 py-4">
          <Link href="/start-onboarding" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-white">
              <Sparkles className="h-4 w-4 text-black" />
            </div>
            <span className="font-semibold tracking-tight">EnglishFlow</span>
          </Link>
          <LogoutButton />
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-10">
        {result?.done ? (
          <section className="ef-card space-y-6 rounded-xl border border-border bg-card/60 p-8 text-center">
            <p className="text-sm text-muted-foreground">Placement complete</p>
            <h1 className="text-3xl font-semibold tracking-tight">
              Your level: {result.current_level}
            </h1>
            <p className="text-sm text-muted-foreground">
              Sub-level {result.placement_score}/10 · {result.questions_asked} questions
            </p>
            <p className="text-sm text-muted-foreground">
              Create a personalized weekly path from skills in your zone, or go to
              the dashboard and build it later. Retaking placement later will reset
              your current path.
            </p>
            {error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
            <div className="flex flex-col items-stretch gap-3 sm:items-center">
              <Button
                type="button"
                size="lg"
                disabled={assembling}
                onClick={goToRoadmap}
              >
                {assembling ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating path…
                  </>
                ) : (
                  <>
                    Create my path
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
              <Button asChild variant="ghost" size="lg" disabled={assembling}>
                <Link href="/dashboard">Go to dashboard</Link>
              </Button>
            </div>
          </section>
        ) : (
          <>
            <div className="mb-8">
              <p className="text-sm text-muted-foreground">Step 2 of 2</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight">
                Placement Test
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Based on your survey, we&apos;ll find your CEFR level.
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                Adaptive test ({minQ}–{maxQ} questions). We stop early when we are
                confident about your level.
              </p>
            </div>

            {error && !question ? (
              <p className="mb-4 text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}

            {question ? (
              <section className="ef-card rounded-xl border border-border bg-card/60 p-6">
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">
                    Answered {asked} / max {maxQ}
                  </Badge>
                  <Badge variant="outline">{question.cefr_level}</Badge>
                  <Badge variant="outline">{question.question_type}</Badge>
                </div>
                {question.passage ? (
                  <div className="mb-5 border-l-2 border-primary/40 pl-4">
                    <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                      Passage
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
                      {question.passage}
                    </p>
                  </div>
                ) : null}
                <p className="text-base font-medium leading-relaxed">{question.stem}</p>

                {question.question_type === "mcq" && question.options?.length ? (
                  <div className="mt-5 grid gap-2">
                    {question.options.map((option) => {
                      const selected = answer === option;
                      return (
                        <button
                          key={option}
                          type="button"
                          onClick={() => {
                            setAnswer(option);
                            setError(null);
                          }}
                          className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                            selected
                              ? "border-primary bg-primary/15 text-foreground"
                              : "border-border bg-background/40 text-muted-foreground hover:border-primary/40 hover:text-foreground"
                          }`}
                        >
                          {option}
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <Input
                    className="mt-5"
                    value={answer}
                    onChange={(e) => {
                      setAnswer(e.target.value);
                      setError(null);
                    }}
                    placeholder="Your answer"
                  />
                )}

                {error ? (
                  <p className="mt-4 text-sm text-destructive" role="alert">
                    {error}
                  </p>
                ) : null}

                <div className="mt-6 flex justify-end">
                  <Button
                    type="button"
                    size="lg"
                    disabled={submitting || !answer.trim()}
                    onClick={handleSubmitAnswer}
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Checking…
                      </>
                    ) : (
                      <>
                        Continue
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>
              </section>
            ) : null}
          </>
        )}
      </main>
    </div>
  );
}
