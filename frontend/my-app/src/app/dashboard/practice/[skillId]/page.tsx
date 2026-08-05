"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, Loader2, X } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import LessonMiniUnit from "@/components/lesson/LessonMiniUnit";
import LessonQaPanel from "@/components/lesson/LessonQaPanel";
import LessonContentWindow from "@/components/lesson/LessonContentWindow";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  completeSkillLesson,
  fetchSkillLesson,
  type SkillLessonResponse,
} from "@/lib/lesson";
import {
  fetchSkillQuestions,
  submitQuizAnswer,
  type SkillQuizQuestion,
} from "@/lib/quiz";

const MASTERY_PASS = 0.7;

type Phase = "learn" | "practice";

export default function PracticeSkillPage() {
  const router = useRouter();
  const params = useParams();
  const skillId = Number(params.skillId);

  const [phase, setPhase] = useState<Phase>("practice");
  const [lessonMeta, setLessonMeta] = useState<SkillLessonResponse | null>(null);
  const [questions, setQuestions] = useState<SkillQuizQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [completingLesson, setCompletingLesson] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{
    correct: boolean;
    mastery: number;
    explanation: string | null;
  } | null>(null);
  const [mastery, setMastery] = useState<number | null>(null);

  const loadPractice = useCallback(async () => {
    const qs = await fetchSkillQuestions(skillId, 5);
    setQuestions(qs);
    if (qs.length === 0) {
      setError(
        "Practice quiz is not ready for this skill yet. Finish Learn if available, then ask an admin to generate & publish quiz questions.",
      );
    } else {
      setError(null);
    }
  }, [skillId]);

  const openPractice = useCallback(async () => {
    setPhase("practice");
    if (questions.length > 0) return;
    setLoading(true);
    try {
      await loadPractice();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load practice");
    } finally {
      setLoading(false);
    }
  }, [loadPractice, questions.length]);

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
      const lesson = await fetchSkillLesson(skillId);
      setLessonMeta(lesson);
      setMastery(lesson.mastery);
      const startLearn = lesson.learn_available && !lesson.can_skip;
      setPhase(startLearn ? "learn" : "practice");
      if (!startLearn) {
        await loadPractice();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load practice");
    } finally {
      setLoading(false);
    }
  }, [skillId, loadPractice]);

  useEffect(() => {
    void load();
  }, [load]);

  const current = questions[index];
  const masteryPct = mastery != null ? Math.round(mastery * 100) : null;
  const readyToComplete = mastery != null && mastery >= MASTERY_PASS;
  const learnDone = Boolean(lessonMeta?.lesson_completed || lessonMeta?.can_skip);
  const hasLearn = Boolean(lessonMeta?.learn_available && lessonMeta.lesson);

  async function handleLessonFinished() {
    setCompletingLesson(true);
    setError(null);
    try {
      const packIndex = lessonMeta?.lesson?.pack_index ?? 0;
      const updated = await completeSkillLesson(skillId, packIndex);
      setLessonMeta(updated);
      if (updated.lesson_completed || updated.can_skip) {
        setPhase("practice");
        setLoading(true);
        await loadPractice();
      } else {
        // More micro-lessons remain in the pack — stay on Learn.
        setPhase("learn");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete lesson");
    } finally {
      setCompletingLesson(false);
      setLoading(false);
    }
  }

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
      void loadPractice();
      return;
    }
    setIndex((i) => i + 1);
  }

  const showReviewLearn =
    phase === "practice" &&
    lessonMeta?.learn_available &&
    lessonMeta.lesson != null;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader />

      <main className="mx-auto max-w-2xl px-6 py-10">
        <>
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <Button asChild variant="ghost" size="sm" className="-ml-2">
                <Link href="/dashboard">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to path
                </Link>
              </Button>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight">
                This week
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Learn the skill, then practice until mastery ≥ 70%.
              </p>
              {hasLearn ? (
                <ol className="mt-3 flex flex-wrap gap-2 text-xs">
                  <li
                    className={`rounded-md border px-2.5 py-1 ${
                      phase === "learn"
                        ? "border-primary bg-primary/10 text-foreground"
                        : learnDone
                          ? "border-[#346538]/30 bg-[#EDF3EC] text-[#346538]"
                          : "border-border text-muted-foreground"
                    }`}
                  >
                    1. Learn
                    {lessonMeta?.pack_total && lessonMeta.pack_total > 1
                      ? ` ${lessonMeta.pack_completed_count ?? 0}/${lessonMeta.pack_total}`
                      : ""}
                    {learnDone && phase !== "learn" ? " ✓" : ""}
                  </li>
                  <li
                    className={`rounded-md border px-2.5 py-1 ${
                      phase === "practice"
                        ? "border-primary bg-primary/10 text-foreground"
                        : "border-border text-muted-foreground"
                    }`}
                  >
                    2. Practice quiz
                  </li>
                  <li
                    className={`rounded-md border px-2.5 py-1 ${
                      readyToComplete
                        ? "border-[#346538]/30 bg-[#EDF3EC] text-[#346538]"
                        : "border-border text-muted-foreground"
                    }`}
                  >
                    3. Complete week
                    {readyToComplete ? " ✓" : ""}
                  </li>
                </ol>
              ) : null}
              {showReviewLearn ? (
                <button
                  type="button"
                  className="mt-2 text-sm text-[#1F6C9F] underline-offset-2 hover:underline"
                  onClick={() => setPhase("learn")}
                >
                  Review lesson
                </button>
              ) : null}
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
              {phase === "learn" ? "Opening lesson…" : "Loading questions…"}
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
                {current.toeic_part ? (
                  <Badge variant="outline">{current.toeic_part.toUpperCase()}</Badge>
                ) : null}
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
                {current.question_type === "fix_grammar"
                  ? "Fix the sentence"
                  : current.stem}
              </p>
              {current.question_type === "fix_grammar" ? (
                <p className="mt-3 rounded-lg border border-border bg-muted/40 px-4 py-3 text-sm leading-relaxed text-foreground/90">
                  {current.stem}
                </p>
              ) : null}

              {feedback ? (
                <div className="mt-5 space-y-4">
                  <div
                    className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${
                      feedback.correct
                        ? "border-[#346538]/30 bg-[#EDF3EC] text-[#346538]"
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
                    <Button
                      type="button"
                      size="lg"
                      className="w-full"
                      onClick={goNext}
                    >
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
                  ) : current.question_type === "cloze" ? (
                    <div className="mt-5 space-y-3">
                      {current.options?.length ? (
                        <div className="grid gap-2">
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
                          value={answer}
                          onChange={(e) => {
                            setAnswer(e.target.value);
                            setError(null);
                          }}
                          placeholder="Fill the blank"
                        />
                      )}
                    </div>
                  ) : (
                    <Input
                      className="mt-5"
                      value={answer}
                      onChange={(e) => {
                        setAnswer(e.target.value);
                        setError(null);
                      }}
                      placeholder={
                        current.question_type === "fix_grammar"
                          ? "Type the corrected sentence"
                          : "Your answer"
                      }
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
        </>

        {phase === "learn" && lessonMeta?.lesson ? (
          <LessonContentWindow
            open
            title={
              lessonMeta.pack_total && lessonMeta.pack_total > 1
                ? `${lessonMeta.lesson.title} (${(lessonMeta.pack_completed_count ?? 0) + 1}/${lessonMeta.pack_total})`
                : lessonMeta.lesson.title
            }
            dismissible={Boolean(lessonMeta.can_skip)}
            onClose={() => {
              void openPractice();
            }}
          >
            {completingLesson ? (
              <div className="flex items-center justify-center gap-2 py-16 text-[#787774]">
                <Loader2 className="h-5 w-5 animate-spin" />
                {lessonMeta?.lesson_completed
                  ? "Opening practice…"
                  : "Saving progress…"}
              </div>
            ) : (
              <LessonMiniUnit
                key={`${lessonMeta.lesson.id}-${lessonMeta.lesson.pack_index ?? 0}`}
                skillId={skillId}
                title={lessonMeta.lesson.title}
                objective={lessonMeta.lesson.objective}
                content={lessonMeta.lesson.content}
                packIndex={lessonMeta.lesson.pack_index ?? 0}
                packLabel={
                  lessonMeta.pack_total && lessonMeta.pack_total > 1
                    ? `${(lessonMeta.pack_completed_count ?? 0) + 1}/${lessonMeta.pack_total}`
                    : null
                }
                onFinished={() => void handleLessonFinished()}
                embedded
              />
            )}
          </LessonContentWindow>
        ) : null}

        {phase === "learn" &&
        lessonMeta?.lesson &&
        !completingLesson ? (
          <LessonQaPanel
            skillId={skillId}
            lessonTitle={lessonMeta.lesson.title}
          />
        ) : null}
      </main>
    </div>
  );
}
