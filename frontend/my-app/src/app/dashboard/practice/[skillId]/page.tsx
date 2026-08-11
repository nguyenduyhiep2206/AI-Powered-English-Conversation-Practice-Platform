"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import LessonMiniUnit from "@/components/lesson/LessonMiniUnit";
import { PracticeShell } from "@/components/practice/PracticeShell";
import { QaDock } from "@/components/practice/QaDock";
import { QuizCard } from "@/components/practice/QuizCard";
import type { StepChip, StepChipId } from "@/components/practice/StepChips";
import {
  completeSkillLesson,
  fetchSkillLesson,
  type SkillLesson,
  type SkillLessonResponse,
} from "@/lib/lesson";
import {
  fetchSkillQuestions,
  submitQuizAnswer,
  type SkillQuizQuestion,
} from "@/lib/quiz";
import { cn } from "@/lib/utils";

const MASTERY_PASS = 0.7;

type Phase = "learn" | "practice";

export default function PracticeSkillPage() {
  const router = useRouter();
  const params = useParams();
  const skillId = Number(params.skillId);

  const [phase, setPhase] = useState<Phase>("practice");
  const [lessonMeta, setLessonMeta] = useState<SkillLessonResponse | null>(null);
  const [viewPackIndex, setViewPackIndex] = useState(0);
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
  const [learnStepIndex, setLearnStepIndex] = useState(0);

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

  const syncViewPack = useCallback((meta: SkillLessonResponse) => {
    const fromLesson = meta.lesson?.pack_index;
    if (typeof fromLesson === "number") {
      setViewPackIndex(fromLesson);
      return;
    }
    setViewPackIndex(0);
  }, []);

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
      syncViewPack(lesson);
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
  }, [skillId, loadPractice, syncViewPack]);

  useEffect(() => {
    void load();
  }, [load]);

  const packList: SkillLesson[] = useMemo(() => {
    if (lessonMeta?.pack?.length) {
      return [...lessonMeta.pack].sort(
        (a, b) => (a.pack_index ?? 0) - (b.pack_index ?? 0),
      );
    }
    return lessonMeta?.lesson ? [lessonMeta.lesson] : [];
  }, [lessonMeta]);

  const packTotal = lessonMeta?.pack_total ?? packList.length;
  const currentProgressIndex = lessonMeta?.lesson?.pack_index ?? 0;
  const learnDone = Boolean(lessonMeta?.lesson_completed || lessonMeta?.can_skip);
  const reviewingLearn = phase === "learn" && learnDone;

  const canViewPack = useCallback(
    (packIdx: number) => {
      if (!packList.some((p) => (p.pack_index ?? 0) === packIdx)) return false;
      if (learnDone) return true;
      return packIdx <= currentProgressIndex;
    },
    [packList, learnDone, currentProgressIndex],
  );

  const displayedLesson =
    packList.find((p) => (p.pack_index ?? 0) === viewPackIndex) ??
    lessonMeta?.lesson ??
    null;

  const viewingPastPack =
    phase === "learn" &&
    displayedLesson != null &&
    (displayedLesson.pack_index ?? 0) < currentProgressIndex &&
    !learnDone;

  const current = questions[index];
  const masteryPct = mastery != null ? Math.round(mastery * 100) : null;
  const readyToComplete = mastery != null && mastery >= MASTERY_PASS;
  const hasLearn = Boolean(lessonMeta?.learn_available && packList.length > 0);

  async function handleLessonFinished() {
    if (reviewingLearn || viewingPastPack) {
      const nextIdx = viewPackIndex + 1;
      if (canViewPack(nextIdx)) {
        setViewPackIndex(nextIdx);
        setLearnStepIndex(0);
        return;
      }
      setPhase("practice");
      if (questions.length === 0) {
        setLoading(true);
        try {
          await loadPractice();
        } finally {
          setLoading(false);
        }
      }
      return;
    }

    setCompletingLesson(true);
    setError(null);
    try {
      const packIndex = displayedLesson?.pack_index ?? viewPackIndex;
      const updated = await completeSkillLesson(skillId, packIndex);
      setLessonMeta(updated);
      syncViewPack(updated);
      if (updated.lesson_completed || updated.can_skip) {
        setPhase("practice");
        setLoading(true);
        await loadPractice();
      } else {
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

  function openLearnAtPack(packIdx: number) {
    if (!canViewPack(packIdx)) return;
    setViewPackIndex(packIdx);
    setLearnStepIndex(0);
    setPhase("learn");
  }

  function goPrevPack() {
    const prev = viewPackIndex - 1;
    if (canViewPack(prev)) {
      setViewPackIndex(prev);
      setLearnStepIndex(0);
    }
  }

  const showReviewLearn =
    phase === "practice" &&
    lessonMeta?.learn_available &&
    packList.length > 0;

  const packCompleted = lessonMeta?.pack_completed_count ?? 0;
  const currentPackPart = Math.min(viewPackIndex + 1, Math.max(packTotal, 1));
  const learnPackDetail =
    packTotal > 1
      ? reviewingLearn
        ? "Review"
        : `${packCompleted}/${packTotal}`
      : undefined;
  const lessonPackLabel =
    packTotal > 1
      ? reviewingLearn
        ? `Review · Part ${currentPackPart}/${packTotal}`
        : `Part ${currentPackPart}/${packTotal}`
      : null;

  const shellTitle =
    lessonMeta?.skill_title?.trim() ||
    displayedLesson?.title ||
    "This week";

  function handleStepSelect(id: StepChipId) {
    if (id === "learn") {
      if (hasLearn) {
        openLearnAtPack(learnDone ? 0 : currentProgressIndex);
      }
      return;
    }
    if (id === "practice") {
      if (phase === "practice") return;
      if (lessonMeta?.can_skip || learnDone) {
        void openPractice();
      }
      return;
    }
    if (id === "path") {
      router.push("/dashboard");
    }
  }

  const selectableStepIds: StepChipId[] = [];
  if (hasLearn && phase !== "learn") selectableStepIds.push("learn");
  if (phase !== "practice" && (lessonMeta?.can_skip || learnDone)) {
    selectableStepIds.push("practice");
  }
  selectableStepIds.push("path");

  const steps: StepChip[] = hasLearn
    ? [
        {
          id: "learn",
          label: "Learn",
          detail: learnPackDetail,
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

  const showPackNav = phase === "learn" && packTotal > 1;

  return (
    <PracticeShell
      title={shellTitle}
      lessonTitle={displayedLesson?.title ?? null}
      masteryPct={masteryPct}
      readyToComplete={readyToComplete}
      steps={steps}
      showSteps={hasLearn || questions.length > 0 || phase === "practice"}
      onStepSelect={handleStepSelect}
      selectableStepIds={selectableStepIds}
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
              className="mb-5 rounded-2xl bg-[#FFE4E6] px-4 py-3 text-[0.875rem] text-[#BE123C] ring-1 ring-[#E85D04]/25"
            >
              {error}
            </div>
          ) : null}
          {showReviewLearn ? (
            <button
              type="button"
              className="mb-4 text-[0.875rem] font-medium text-[#9A3412] hover:text-[#E85D04] cursor-pointer"
              onClick={() => openLearnAtPack(0)}
            >
              Review lesson
            </button>
          ) : null}
          {phase === "learn" && lessonMeta?.can_skip ? (
            <button
              type="button"
              className="mb-4 mr-4 text-[0.875rem] font-medium text-[#9A3412] hover:text-[#E85D04] cursor-pointer"
              onClick={() => void openPractice()}
            >
              Skip to practice
            </button>
          ) : null}
          {showPackNav ? (
            <nav
              aria-label="Lesson pack"
              className="mb-4 flex flex-wrap items-center gap-2"
            >
              {packList.map((p) => {
                const idx = p.pack_index ?? 0;
                const active = idx === viewPackIndex;
                const enabled = canViewPack(idx);
                return (
                  <button
                    key={`${p.id}-${idx}`}
                    type="button"
                    disabled={!enabled}
                    onClick={() => openLearnAtPack(idx)}
                    className={cn(
                      "inline-flex min-h-9 items-center rounded-2xl px-3 text-[0.75rem] font-medium ring-1 transition-colors",
                      active &&
                        "bg-[#FFE8D6] text-[#9A3412] ring-[#E85D04]/35",
                      !active &&
                        enabled &&
                        "bg-white text-[#6B6258] ring-[#E9D7C9] hover:ring-[#E85D04]/40 cursor-pointer",
                      !enabled &&
                        "bg-white/60 text-[#A89F94] ring-[#E9D7C9] opacity-70",
                    )}
                  >
                    Lesson {idx + 1}
                  </button>
                );
              })}
            </nav>
          ) : null}
        </>
      }
      lesson={
        phase === "learn" && displayedLesson ? (
          completingLesson ? (
            <div className="flex items-center justify-center gap-2 py-16 text-[#6B6258]">
              <Loader2 className="h-5 w-5 animate-spin" />
              Saving progress…
            </div>
          ) : (
            <LessonMiniUnit
              key={`${displayedLesson.id}-${displayedLesson.pack_index ?? 0}`}
              skillId={skillId}
              title={displayedLesson.title}
              objective={displayedLesson.objective}
              content={displayedLesson.content}
              packIndex={displayedLesson.pack_index ?? viewPackIndex}
              packLabel={lessonPackLabel}
              reviewMode={reviewingLearn || viewingPastPack}
              onStepChange={({ index: stepIndex }) =>
                setLearnStepIndex(stepIndex)
              }
              onBackFromStart={
                canViewPack(viewPackIndex - 1) ? goPrevPack : undefined
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
        phase === "learn" && displayedLesson && !completingLesson ? (
          <QaDock
            skillId={skillId}
            lessonTitle={displayedLesson.title}
            showSuggestions={learnStepIndex > 0}
          />
        ) : null
      }
    />
  );
}
