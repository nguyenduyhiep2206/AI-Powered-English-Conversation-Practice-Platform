"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import LogoutButton from "@/components/ui/LogoutButton";
import { fetchOnboardingStatus } from "@/lib/onboarding-status";
import {
  fetchSurveyQuestions,
  submitSurvey,
  type SurveyAnswerPayload,
  type SurveyQuestion,
} from "@/lib/survey";

type AnswerState = Record<number, string>;

export default function OnboardingSurveyPage() {
  const router = useRouter();
  const [questions, setQuestions] = useState<SurveyQuestion[]>([]);
  const [answers, setAnswers] = useState<AnswerState>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const status = await fetchOnboardingStatus();
        if (status.onboarding_complete) {
          router.replace("/dashboard");
          return;
        }
        if (status.survey_done) {
          router.replace("/onboarding/placement");
          return;
        }

        const qs = await fetchSurveyQuestions();
        setQuestions(qs);
      } catch (err) {
        if (err instanceof Error && err.message === "SURVEY_ALREADY_DONE") {
          router.replace("/onboarding/placement");
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load survey");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  function setAnswer(questionId: number, value: string) {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const missing = questions.filter((q) => q.is_required && !answers[q.id]?.trim());
    if (missing.length > 0) {
      setError("Please answer all required questions");
      return;
    }

    const payload: SurveyAnswerPayload[] = questions
      .filter((q) => answers[q.id])
      .map((q) => ({
        question_id: q.id,
        answer:
          q.question_type === "text"
            ? { text: answers[q.id] }
            : { value: answers[q.id] },
      }));

    setSubmitting(true);
    try {
      await submitSurvey(payload);
      router.replace("/onboarding/placement");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit survey");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

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
        <div className="mb-8">
          <p className="text-sm text-muted-foreground">Step 1 of 2</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Quick Survey</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Help us personalize your placement test and learning plan.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {questions.map((question, index) => (
            <fieldset
              key={question.id}
              className="ef-card rounded-xl border border-border bg-card/60 p-6"
            >
              <legend className="px-1 text-sm font-medium">
                {index + 1}. {question.prompt}
                {question.is_required && <span className="text-destructive"> *</span>}
              </legend>

              {question.question_type === "text" ? (
                <div className="mt-4">
                  <Label htmlFor={`q-${question.id}`} className="sr-only">
                    {question.prompt}
                  </Label>
                  <Input
                    id={`q-${question.id}`}
                    value={answers[question.id] ?? ""}
                    onChange={(e) => setAnswer(question.id, e.target.value)}
                    placeholder="Your answer"
                    className="mt-2"
                  />
                </div>
              ) : (
                <div className="mt-4 grid gap-2">
                  {(question.options ?? []).map((option) => {
                    const selected = answers[question.id] === option.value;
                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setAnswer(question.id, option.value)}
                        className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                          selected
                            ? "border-primary bg-primary/15 text-foreground"
                            : "border-border bg-background/40 text-muted-foreground hover:border-primary/40 hover:text-foreground"
                        }`}
                      >
                        {option.label}
                      </button>
                    );
                  })}
                </div>
              )}
            </fieldset>
          ))}

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}

          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
            <Button type="button" variant="ghost" asChild>
              <Link href="/start-onboarding">Back</Link>
            </Button>
            <Button type="submit" size="lg" disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  Continue to placement test
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </div>
        </form>
      </main>
    </div>
  );
}
