"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Loader2, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import LogoutButton from "@/components/ui/LogoutButton";
import {
  fetchLevelChallengeQuestions,
  submitLevelChallenge,
  type LevelChallengeResult,
} from "@/lib/level-challenge";
import type { PlacementQuestion } from "@/lib/placement";
import { assembleRoadmap } from "@/lib/roadmap";

type AnswerState = Record<number, string>;

export default function LevelChallengePage() {
  const router = useRouter();
  const [targetLevel, setTargetLevel] = useState<string | null>(null);
  const [questions, setQuestions] = useState<PlacementQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<AnswerState>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [assembling, setAssembling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LevelChallengeResult | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchLevelChallengeQuestions();
        setTargetLevel(data.target_level);
        setQuestions(data.questions);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load level challenge",
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const current = questions[index];
  const allAnswered =
    questions.length > 0 &&
    questions.every((q) => Boolean(answers[q.id]?.trim()));
  const isLast = index === questions.length - 1;

  function setAnswer(value: string) {
    if (!current) return;
    setAnswers((prev) => ({ ...prev, [current.id]: value }));
    setError(null);
  }

  async function handleSubmit() {
    if (!targetLevel) {
      setError("Missing target level");
      return;
    }
    if (!allAnswered) {
      setError("Please answer all questions before submitting");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = questions.map((q) => ({
        question_id: q.id,
        answer: answers[q.id].trim(),
      }));
      const data = await submitLevelChallenge({
        target_level: targetLevel,
        answers: payload,
      });
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to submit level challenge",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function buildNewPath() {
    setAssembling(true);
    setError(null);
    try {
      await assembleRoadmap({ max_steps: 10 });
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
      <div className="dark flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="dark min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex items-center justify-between px-6 py-4">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white">
              <Sparkles className="h-4 w-4 text-black" />
            </div>
            <span className="font-semibold tracking-tight">EnglishFlow</span>
          </Link>
          <LogoutButton />
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-10">
        {result ? (
          <section className="space-y-6 rounded-xl border border-border bg-card/60 p-8 text-center">
            <p className="text-sm text-muted-foreground">
              {result.passed ? "Challenge passed" : "Challenge not passed"}
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">
              {result.passed
                ? `Welcome to ${result.current_level}`
                : `Still ${result.current_level}`}
            </h1>
            <p className="text-sm text-muted-foreground">
              Score {result.correct_count}/{result.total} on{" "}
              {result.target_level}
              {result.passed && result.placement_score != null
                ? ` · new sub-level ${result.placement_score}/10`
                : null}
            </p>
            <p className="text-sm text-muted-foreground">
              {result.passed
                ? "Your old path was cleared. Build a new path for this level."
                : "Keep practicing at your current level. You can try again later."}
            </p>
            {error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
            <div className="flex flex-col items-stretch gap-3 sm:items-center">
              {result.passed ? (
                <Button
                  type="button"
                  size="lg"
                  disabled={assembling}
                  onClick={buildNewPath}
                >
                  {assembling ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Building path…
                    </>
                  ) : (
                    <>
                      Build new path
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
              ) : null}
              <Button
                asChild
                variant={result.passed ? "ghost" : "default"}
                size="lg"
                disabled={assembling}
              >
                <Link href="/dashboard">Back to dashboard</Link>
              </Button>
            </div>
          </section>
        ) : (
          <>
            <div className="mb-8">
              <p className="text-sm text-muted-foreground">
                Level challenge
              </p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight">
                Challenge {targetLevel ?? "next level"}
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Answer 6 questions at the next CEFR band. Pass with 4 or more
                correct to move up one level.
              </p>
              <Button asChild variant="ghost" size="sm" className="mt-3 -ml-2">
                <Link href="/dashboard">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to dashboard
                </Link>
              </Button>
            </div>

            {error && !current ? (
              <p className="mb-4 text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}

            {current ? (
              <section className="rounded-xl border border-border bg-card/60 p-6">
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">
                    Question {index + 1} / {questions.length}
                  </Badge>
                  <Badge variant="outline">{current.cefr_level}</Badge>
                  <Badge variant="outline">{current.question_type}</Badge>
                </div>
                {current.passage ? (
                  <div className="mb-5 border-l-2 border-primary/40 pl-4">
                    <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                      Passage
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
                      {current.passage}
                    </p>
                  </div>
                ) : null}
                <p className="text-base font-medium leading-relaxed">
                  {current.stem}
                </p>

                {current.question_type === "mcq" && current.options?.length ? (
                  <div className="mt-5 grid gap-2">
                    {current.options.map((option) => {
                      const selected = answers[current.id] === option;
                      return (
                        <button
                          key={option}
                          type="button"
                          onClick={() => setAnswer(option)}
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
                    value={answers[current.id] ?? ""}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Your answer"
                  />
                )}

                {error ? (
                  <p className="mt-4 text-sm text-destructive" role="alert">
                    {error}
                  </p>
                ) : null}

                <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={index === 0}
                    onClick={() => {
                      setError(null);
                      setIndex((i) => Math.max(0, i - 1));
                    }}
                  >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                  </Button>

                  {isLast ? (
                    <Button
                      type="button"
                      size="lg"
                      disabled={submitting || !allAnswered}
                      onClick={handleSubmit}
                    >
                      {submitting ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Submitting…
                        </>
                      ) : (
                        <>
                          Submit challenge
                          <ArrowRight className="ml-2 h-4 w-4" />
                        </>
                      )}
                    </Button>
                  ) : (
                    <Button
                      type="button"
                      size="lg"
                      disabled={!answers[current.id]?.trim()}
                      onClick={() => {
                        setError(null);
                        setIndex((i) =>
                          Math.min(questions.length - 1, i + 1),
                        );
                      }}
                    >
                      Next
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  )}
                </div>
              </section>
            ) : null}
          </>
        )}
      </main>
    </div>
  );
}
