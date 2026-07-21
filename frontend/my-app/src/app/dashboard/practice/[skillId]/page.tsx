"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, Loader2, Sparkles, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import LogoutButton from "@/components/ui/LogoutButton";
import {
  fetchSkillQuestions,
  submitQuizAnswer,
  type SkillQuizQuestion,
} from "@/lib/quiz";

const MASTERY_PASS = 0.7;

export default function PracticeSkillPage() {
  const router = useRouter();
  const params = useParams();
  const skillId = Number(params.skillId);

  const [questions, setQuestions] = useState<SkillQuizQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{
    correct: boolean;
    mastery: number;
    explanation: string | null;
  } | null>(null);
  const [mastery, setMastery] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!Number.isFinite(skillId) || skillId <= 0) {
      setError("Invalid skill");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    setFeedback(null);
    setAnswer("");
    setIndex(0);
    try {
      const qs = await fetchSkillQuestions(skillId, 5);
      setQuestions(qs);
      if (qs.length === 0) {
        setError("No published questions for this skill yet.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load practice");
    } finally {
      setLoading(false);
    }
  }, [skillId]);

  useEffect(() => {
    void load();
  }, [load]);

  const current = questions[index];
  const masteryPct = mastery != null ? Math.round(mastery * 100) : null;
  const readyToComplete = mastery != null && mastery >= MASTERY_PASS;

  async function handleSubmit() {
    if (!current || !answer.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await submitQuizAnswer(current.id, answer.trim());
      setFeedback({
        correct: result.correct,
        mastery: result.mastery,
        explanation: result.explanation,
      });
      setMastery(result.mastery);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit answer");
    } finally {
      setSubmitting(false);
    }
  }

  function goNext() {
    setFeedback(null);
    setAnswer("");
    if (index + 1 >= questions.length) {
      void load();
      return;
    }
    setIndex((i) => i + 1);
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
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <Button asChild variant="ghost" size="sm" className="-ml-2">
              <Link href="/dashboard">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to path
              </Link>
            </Button>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight">
              Practice
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Answer questions to raise mastery. Reach 70% to complete the week.
            </p>
          </div>
          {masteryPct != null ? (
            <Badge variant={readyToComplete ? "default" : "outline"}>
              Mastery {masteryPct}%
            </Badge>
          ) : null}
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-20 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading questions…
          </div>
        ) : error && !current ? (
          <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-6 text-sm text-destructive">
            {error}
          </div>
        ) : current ? (
          <section className="rounded-xl border border-border bg-card/60 p-6">
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <Badge variant="secondary">
                Question {index + 1} / {questions.length}
              </Badge>
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

            <p className="text-base font-medium leading-relaxed">{current.stem}</p>

            {feedback ? (
              <div className="mt-5 space-y-4">
                <div
                  className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${
                    feedback.correct
                      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
                      : "border-destructive/40 bg-destructive/10 text-destructive"
                  }`}
                >
                  {feedback.correct ? (
                    <Check className="mt-0.5 h-4 w-4 shrink-0" />
                  ) : (
                    <X className="mt-0.5 h-4 w-4 shrink-0" />
                  )}
                  <div>
                    <p>{feedback.correct ? "Correct" : "Not quite"}</p>
                    {feedback.explanation ? (
                      <p className="mt-1 text-muted-foreground">
                        {feedback.explanation}
                      </p>
                    ) : null}
                  </div>
                </div>

                {readyToComplete ? (
                  <Button
                    type="button"
                    size="lg"
                    className="w-full"
                    onClick={() => router.push("/dashboard")}
                  >
                    Mastery reached — back to path
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                ) : (
                  <Button type="button" size="lg" className="w-full" onClick={goNext}>
                    Next question
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                )}
              </div>
            ) : (
              <>
                {current.question_type === "mcq" && current.options?.length ? (
                  <div className="mt-5 grid gap-2">
                    {current.options.map((option) => {
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

                <Button
                  type="button"
                  size="lg"
                  className="mt-6 w-full"
                  disabled={submitting || !answer.trim()}
                  onClick={handleSubmit}
                >
                  {submitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Checking…
                    </>
                  ) : (
                    "Check answer"
                  )}
                </Button>
              </>
            )}
          </section>
        ) : null}
      </main>
    </div>
  );
}
