"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Loader2, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import LogoutButton from "@/components/ui/LogoutButton";
import { fetchOnboardingStatus } from "@/lib/onboarding-status";
import {
  fetchPlacementQuestions,
  submitPlacement,
  type PlacementQuestion,
  type PlacementResult,
} from "@/lib/placement";

type AnswerState = Record<number, string>;

export default function PlacementPage() {
  const router = useRouter();
  const [questions, setQuestions] = useState<PlacementQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<AnswerState>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PlacementResult | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const status = await fetchOnboardingStatus();
        if (status.onboarding_complete || status.placement_done) {
          router.replace("/dashboard");
          return;
        }
        if (!status.survey_done) {
          router.replace("/onboarding");
          return;
        }

        const qs = await fetchPlacementQuestions();
        setQuestions(qs);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load placement");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  const current = questions[index];
  const allAnswered =
    questions.length > 0 && questions.every((q) => Boolean(answers[q.id]?.trim()));
  const isLast = index === questions.length - 1;

  function setAnswer(value: string) {
    if (!current) return;
    setAnswers((prev) => ({ ...prev, [current.id]: value }));
    setError(null);
  }

  async function handleSubmit() {
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
      const data = await submitPlacement(payload);
      setResult(data);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit placement");
    } finally {
      setSubmitting(false);
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
          <Link href="/start-onboarding" className="flex items-center gap-2">
            <div className="ef-grad-hero flex h-8 w-8 items-center justify-center rounded-lg bg-white">
              <Sparkles className="h-4 w-4 text-black" />
            </div>
            <span className="font-semibold tracking-tight">EnglishFlow</span>
          </Link>
          <LogoutButton />
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-10">
        {result ? (
          <section className="ef-card space-y-6 rounded-xl border border-border bg-card/60 p-8 text-center">
            <p className="text-sm text-muted-foreground">Placement complete</p>
            <h1 className="text-3xl font-semibold tracking-tight">
              Your level: {result.current_level}
            </h1>
            <p className="text-sm text-muted-foreground">
              Score {result.correct_count}/{result.total} ({result.placement_score}/10)
            </p>
            <p className="text-sm text-muted-foreground">
              You can create your learning roadmap when you are ready.
            </p>
            <Button asChild size="lg">
              <Link href="/dashboard">
                Go to dashboard
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </section>
        ) : (
          <>
            <div className="mb-8">
              <p className="text-sm text-muted-foreground">Step 2 of 2</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight">Placement Test</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Answer 10 questions so we can place you at the right CEFR level.
              </p>
            </div>

            {error && !current && (
              <p className="mb-4 text-sm text-destructive" role="alert">
                {error}
              </p>
            )}

            {current && (
              <section className="ef-card rounded-xl border border-border bg-card/60 p-6">
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">
                    Question {index + 1} / {questions.length}
                  </Badge>
                  <Badge variant="outline">{current.cefr_level}</Badge>
                  <Badge variant="outline">{current.question_type}</Badge>
                </div>
                <p className="text-base font-medium leading-relaxed">{current.stem}</p>

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

                {error && (
                  <p className="mt-4 text-sm text-destructive" role="alert">
                    {error}
                  </p>
                )}

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
                          Submitting...
                        </>
                      ) : (
                        <>
                          Submit placement
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
                        setIndex((i) => Math.min(questions.length - 1, i + 1));
                      }}
                    >
                      Next
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  )}
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
