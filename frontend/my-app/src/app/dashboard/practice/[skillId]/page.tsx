"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import LessonMiniUnit from "@/components/lesson/LessonMiniUnit";
import { PracticeShell } from "@/components/practice/PracticeShell";
import { QaDock } from "@/components/practice/QaDock";
import { QuizCard } from "@/components/practice/QuizCard";
import type { StepChip } from "@/components/practice/StepChips";
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

  const steps: StepChip[] = hasLearn
    ? [
        {
          id: "learn",
          label: "Learn",
          detail:
            lessonMeta?.pack_total && lessonMeta.pack_total > 1
              ? `${lessonMeta.pack_completed_count ?? 0}/${lessonMeta.pack_total}`
              : undefined,
          state:
            phase === "learn" ? "active" : learnDone ? "done" : "upcoming",
        },
        {
          id: "practice",
          label: "Practice quiz",
          state: phase === "practice" ? "active" : "upcoming",
        },
        {
          id: "path",
          label: "Path",
          state: readyToComplete ? "done" : "upcoming",
        },
      ]
    : [
        {
          id: "practice",
          label: "Practice quiz",
          state: phase === "practice" ? "active" : "upcoming",
        },
        {
          id: "path",
          label: "Path",
          state: readyToComplete ? "done" : "upcoming",
        },
      ];

  return (
    <PracticeShell
      title={lessonMeta?.lesson?.title ?? "This week"}
      masteryPct={masteryPct}
      readyToComplete={readyToComplete}
      steps={steps}
      showSteps={hasLearn || questions.length > 0 || phase === "practice"}
      phase={phase === "learn" ? "learn" : "practice"}
      loading={loading}
      loadingLabel={
        phase === "learn" ? "Opening lesson…" : "Loading questions…"
      }
      banner={
        <>
          {error && !current && phase === "practice" ? (
            <div
              role="alert"
              className="mb-5 rounded-2xl bg-[#FFF0EE] px-4 py-3 text-[0.875rem] text-[#C24B3A] ring-1 ring-[#FF8A6B]/25"
            >
              {error}
            </div>
          ) : null}
          {showReviewLearn ? (
            <button
              type="button"
              className="mb-4 text-[0.875rem] font-medium text-[#7B6EF6] hover:text-[#6758E8]"
              onClick={() => setPhase("learn")}
            >
              Review lesson
            </button>
          ) : null}
          {phase === "learn" && lessonMeta?.can_skip ? (
            <button
              type="button"
              className="mb-4 text-[0.875rem] font-medium text-[#7B6EF6] hover:text-[#6758E8]"
              onClick={() => void openPractice()}
            >
              Skip to practice
            </button>
          ) : null}
        </>
      }
      lesson={
        phase === "learn" && lessonMeta?.lesson ? (
          completingLesson ? (
            <div className="flex items-center justify-center gap-2 py-16 text-[#8A8396]">
              <Loader2 className="h-5 w-5 animate-spin" />
              Saving progress…
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
          )
        ) : null
      }
      quiz={
        current ? (
          <QuizCard
            question={current}
            index={index}
            total={questions.length}
            answer={answer}
            onAnswerChange={(v) => {
              setAnswer(v);
              setError(null);
            }}
            feedback={
              feedback
                ? {
                    correct: feedback.correct,
                    explanation: feedback.explanation,
                  }
                : null
            }
            submitting={submitting}
            error={error}
            readyToComplete={readyToComplete}
            onSubmit={() => void handleSubmit()}
            onNext={goNext}
            onBackToPath={() => router.push("/dashboard")}
          />
        ) : null
      }
      qa={
        phase === "learn" && lessonMeta?.lesson && !completingLesson ? (
          <QaDock
            skillId={skillId}
            lessonTitle={lessonMeta.lesson.title}
          />
        ) : null
      }
    />
  );
}
