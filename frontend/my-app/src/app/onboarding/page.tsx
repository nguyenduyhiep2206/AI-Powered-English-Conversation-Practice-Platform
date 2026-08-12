"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2 } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { cn } from "@/lib/utils";
import { fetchOnboardingStatus } from "@/lib/onboarding-status";
import { assembleRoadmap } from "@/lib/roadmap";
import {
  fetchSurveyQuestions,
  submitSurvey,
  type LevelResolution,
  type SurveyAnswerPayload,
  type SurveyQuestion,
} from "@/lib/survey";

type WizardStep = "why" | "time" | "know_english" | "level_fork" | "pick_cefr";
type KnowEnglishChoice = "beginner" | "know_some";
type LevelForkChoice = "self_selected" | "placement";
type CefrLevel = "A1" | "A2" | "B1" | "B2" | "C1";

const CEFR_LEVELS: CefrLevel[] = ["A1", "A2", "B1", "B2", "C1"];

const KNOW_ENGLISH_OPTIONS: {
  value: KnowEnglishChoice;
  label: string;
  hint: string;
}[] = [
  {
    value: "beginner",
    label: "I'm just starting out",
    hint: "We'll place you at A1",
  },
  {
    value: "know_some",
    label: "I know some English",
    hint: "Pick your level or take a placement test",
  },
];

const LEVEL_FORK_OPTIONS: {
  value: LevelForkChoice;
  label: string;
  hint: string;
}[] = [
  {
    value: "self_selected",
    label: "I know my level",
    hint: "Choose A1–C1 yourself",
  },
  {
    value: "placement",
    label: "Help me find my level",
    hint: "Optional TOEIC-style placement test",
  },
];

function splitQuestions(questions: SurveyQuestion[]) {
  const why =
    questions.find((q) => q.maps_to_profile_field === "goal") ??
    questions.find((q) =>
      (q.options ?? []).some((o) => o.value === "work" || o.value === "travel"),
    );
  const time =
    questions.find((q) => q.maps_to_profile_field === "daily_time_min") ??
    questions.find((q) =>
      (q.options ?? []).some((o) => o.value === "10" || o.value === "25"),
    );
  if (!why || !time) {
    throw new Error(
      "Survey is not configured for Busuu-style onboarding. Run alembic upgrade head so only goal + daily_time questions are active.",
    );
  }
  return { why, time };
}

function computeTotalSteps(
  knowEnglish: KnowEnglishChoice | null,
  levelFork: LevelForkChoice | null,
): number {
  if (knowEnglish === "beginner") return 3;
  if (knowEnglish === "know_some") {
    if (levelFork === "placement") return 4;
    return 5;
  }
  return 5;
}

function stepIndex(step: WizardStep): number {
  const order: WizardStep[] = [
    "why",
    "time",
    "know_english",
    "level_fork",
    "pick_cefr",
  ];
  return order.indexOf(step) + 1;
}

function optionClass(selected: boolean): string {
  return cn(
    "w-full rounded-2xl px-4 py-3.5 text-left text-[0.9375rem] transition-[background-color,box-shadow,transform] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]",
    selected
      ? "bg-[#FFE8D6] font-semibold text-[#1F1B15] shadow-[0_4px_14px_rgba(232,93,4,0.18)] ring-2 ring-[#E85D04]"
      : "bg-[#FFFAF5] text-[#6B6258] ring-1 ring-[#E9D7C9] hover:bg-white hover:text-[#1F1B15]",
  );
}

export default function OnboardingSurveyPage() {
  const router = useRouter();
  const [whyQuestion, setWhyQuestion] = useState<SurveyQuestion | null>(null);
  const [timeQuestion, setTimeQuestion] = useState<SurveyQuestion | null>(null);
  const [step, setStep] = useState<WizardStep>("why");
  const [whyAnswer, setWhyAnswer] = useState<string | null>(null);
  const [timeAnswer, setTimeAnswer] = useState<string | null>(null);
  const [knowEnglish, setKnowEnglish] = useState<KnowEnglishChoice | null>(
    null,
  );
  const [levelFork, setLevelFork] = useState<LevelForkChoice | null>(null);
  const [cefrLevel, setCefrLevel] = useState<CefrLevel | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalSteps = computeTotalSteps(knowEnglish, levelFork);
  const progress = stepIndex(step) / totalSteps;

  const canContinue = useMemo(() => {
    switch (step) {
      case "why":
        return Boolean(whyAnswer);
      case "time":
        return Boolean(timeAnswer);
      case "know_english":
        return Boolean(knowEnglish);
      case "level_fork":
        return Boolean(levelFork);
      case "pick_cefr":
        return Boolean(cefrLevel);
      default:
        return false;
    }
  }, [step, whyAnswer, timeAnswer, knowEnglish, levelFork, cefrLevel]);

  useEffect(() => {
    async function load() {
      try {
        const status = await fetchOnboardingStatus();
        if (status.onboarding_complete) {
          router.replace("/dashboard");
          return;
        }
        if (status.survey_done) {
          router.replace(
            status.placement_done ? "/dashboard" : "/onboarding/placement",
          );
          return;
        }

        const qs = await fetchSurveyQuestions();
        const { why, time } = splitQuestions(qs);
        setWhyQuestion(why);
        setTimeQuestion(time);
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

  function buildPayload(): SurveyAnswerPayload[] {
    if (!whyQuestion || !timeQuestion || !whyAnswer || !timeAnswer) {
      throw new Error("Please answer all survey questions");
    }
    return [
      { question_id: whyQuestion.id, answer: { value: whyAnswer } },
      { question_id: timeQuestion.id, answer: { value: timeAnswer } },
    ];
  }

  function buildLevelResolution(): LevelResolution {
    if (knowEnglish === "beginner") {
      return { mode: "beginner" };
    }
    if (levelFork === "placement") {
      return { mode: "placement" };
    }
    if (levelFork === "self_selected" && cefrLevel) {
      return { mode: "self_selected", cefr_level: cefrLevel };
    }
    throw new Error("Please complete level selection");
  }

  async function finishSurvey() {
    setError(null);
    setSubmitting(true);
    try {
      const payload = buildPayload();
      const levelResolution = buildLevelResolution();
      const result = await submitSurvey(payload, levelResolution);
      if (result.next_step === "placement") {
        router.replace("/onboarding/placement");
      } else {
        try {
          await assembleRoadmap();
        } catch {
          // non-blocking; dashboard can assemble later
        }
        router.replace("/dashboard");
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit survey");
    } finally {
      setSubmitting(false);
    }
  }

  function handleContinue() {
    setError(null);
    if (step === "why") {
      setStep("time");
      return;
    }
    if (step === "time") {
      setStep("know_english");
      return;
    }
    if (step === "know_english") {
      if (knowEnglish === "beginner") {
        void finishSurvey();
        return;
      }
      setStep("level_fork");
      return;
    }
    if (step === "level_fork") {
      if (levelFork === "placement") {
        void finishSurvey();
        return;
      }
      setStep("pick_cefr");
      return;
    }
    if (step === "pick_cefr") {
      void finishSurvey();
    }
  }

  function handleBack() {
    setError(null);
    if (step === "time") {
      setStep("why");
      return;
    }
    if (step === "know_english") {
      setStep("time");
      return;
    }
    if (step === "level_fork") {
      setLevelFork(null);
      setStep("know_english");
      return;
    }
    if (step === "pick_cefr") {
      setCefrLevel(null);
      setStep("level_fork");
    }
  }

  if (loading) {
    return (
      <div className="relative flex min-h-screen items-center justify-center overflow-x-hidden bg-[#FFF5EB] text-[#1F1B15]">
        <div className="flex items-center gap-2 text-[0.875rem] text-[#8A8178]">
          <Loader2
            className="h-5 w-5 animate-spin text-[#E85D04]"
            aria-hidden
          />
          Loading survey…
        </div>
      </div>
    );
  }

  if (!whyQuestion || !timeQuestion) {
    return (
      <div className="relative min-h-screen overflow-x-hidden bg-[#FFF5EB] text-[#1F1B15]">
        <AppHeader />
        <main className="mx-auto max-w-2xl px-5 py-10 sm:px-8">
          <div
            className="rounded-2xl bg-[#FFE4E6] px-4 py-3 text-[0.875rem] text-[#BE123C] ring-1 ring-[#BE123C]/25"
            role="alert"
          >
            {error ?? "Survey is not configured for Busuu-style onboarding"}
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#FFF5EB] text-[#1F1B15]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 55% 40% at 10% 8%, rgba(232, 93, 4, 0.14), transparent 58%), radial-gradient(ellipse 45% 35% at 90% 70%, rgba(13, 148, 136, 0.1), transparent 55%)",
        }}
      />

      <div className="relative flex min-h-screen flex-col">
        <AppHeader />

        <main className="mx-auto w-full max-w-2xl flex-1 px-5 py-8 sm:px-8 md:py-10">
          <div className="mb-6">
            <div
              className="h-2 w-full overflow-hidden rounded-full bg-[#E9D7C9]"
              role="progressbar"
              aria-valuenow={Math.round(progress * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Survey progress"
            >
              <div
                className="h-full rounded-full bg-[#E85D04] transition-[width] duration-300 ease-out"
                style={{ width: `${Math.round(progress * 100)}%` }}
              />
            </div>
            <p className="mt-2 text-[0.8125rem] font-medium text-[#8A8178]">
              Step {stepIndex(step)} of {totalSteps}
            </p>
          </div>

          <section className="ef-fade-up rounded-[1.75rem] bg-white p-6 shadow-[0_18px_50px_rgba(31,27,21,0.08)] ring-1 ring-[#1F1B15]/06 sm:p-8">
            {step === "why" ? (
              <>
                <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]">
                  {whyQuestion.prompt}
                </h1>
                <div className="mt-5 grid gap-2.5">
                  {(whyQuestion.options ?? []).map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        setWhyAnswer(option.value);
                        setError(null);
                      }}
                      className={optionClass(whyAnswer === option.value)}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </>
            ) : null}

            {step === "time" ? (
              <>
                <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]">
                  {timeQuestion.prompt}
                </h1>
                <div className="mt-5 grid gap-2.5">
                  {(timeQuestion.options ?? []).map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        setTimeAnswer(option.value);
                        setError(null);
                      }}
                      className={optionClass(timeAnswer === option.value)}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </>
            ) : null}

            {step === "know_english" ? (
              <>
                <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]">
                  How much English do you know?
                </h1>
                <p className="mt-2 text-[0.9375rem] leading-relaxed text-[#6B6258]">
                  We&apos;ll use this to place you at the right level.
                </p>
                <div className="mt-5 grid gap-2.5">
                  {KNOW_ENGLISH_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        setKnowEnglish(option.value);
                        setLevelFork(null);
                        setCefrLevel(null);
                        setError(null);
                      }}
                      className={optionClass(knowEnglish === option.value)}
                    >
                      <span className="block font-semibold text-[#1F1B15]">
                        {option.label}
                      </span>
                      <span className="mt-1 block text-[0.8125rem] font-normal text-[#8A8178]">
                        {option.hint}
                      </span>
                    </button>
                  ))}
                </div>
              </>
            ) : null}

            {step === "level_fork" ? (
              <>
                <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]">
                  How should we set your level?
                </h1>
                <div className="mt-5 grid gap-2.5">
                  {LEVEL_FORK_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        setLevelFork(option.value);
                        setCefrLevel(null);
                        setError(null);
                      }}
                      className={optionClass(levelFork === option.value)}
                    >
                      <span className="block font-semibold text-[#1F1B15]">
                        {option.label}
                      </span>
                      <span className="mt-1 block text-[0.8125rem] font-normal text-[#8A8178]">
                        {option.hint}
                      </span>
                    </button>
                  ))}
                </div>
              </>
            ) : null}

            {step === "pick_cefr" ? (
              <>
                <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]">
                  Which level fits you best?
                </h1>
                <p className="mt-2 text-[0.9375rem] leading-relaxed text-[#6B6258]">
                  Pick the CEFR level that matches your current ability.
                </p>
                <div className="mt-5 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                  {CEFR_LEVELS.map((level) => (
                    <button
                      key={level}
                      type="button"
                      onClick={() => {
                        setCefrLevel(level);
                        setError(null);
                      }}
                      className={cn(
                        optionClass(cefrLevel === level),
                        "text-center font-semibold",
                      )}
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </>
            ) : null}

            {error ? (
              <div
                className="mt-5 rounded-2xl bg-[#FFE4E6] px-4 py-3 text-[0.875rem] text-[#BE123C] ring-1 ring-[#BE123C]/25"
                role="alert"
              >
                {error}
              </div>
            ) : null}

            <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
              {step !== "why" ? (
                <button
                  type="button"
                  onClick={handleBack}
                  disabled={submitting}
                  className="inline-flex min-h-11 items-center justify-center rounded-2xl px-4 text-[0.875rem] font-semibold text-[#9A3412] transition-colors hover:bg-[#FFFAF5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] disabled:opacity-60"
                >
                  Back
                </button>
              ) : (
                <Link
                  href="/start-onboarding"
                  className="inline-flex min-h-11 items-center justify-center rounded-2xl px-4 text-[0.875rem] font-semibold text-[#9A3412] transition-colors hover:bg-[#FFFAF5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
                >
                  Back
                </Link>
              )}
              <button
                type="button"
                disabled={submitting || !canContinue}
                aria-busy={submitting}
                onClick={handleContinue}
                className="inline-flex h-11 items-center justify-center rounded-2xl bg-[#E85D04] px-6 text-[0.9375rem] font-semibold text-white shadow-[0_10px_24px_rgba(232,93,4,0.28)] transition-[transform,background-color] duration-200 hover:bg-[#D04F00] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] active:scale-[0.98] disabled:opacity-60"
              >
                {submitting ? (
                  <>
                    <Loader2
                      className="mr-2 h-4 w-4 animate-spin"
                      aria-hidden
                    />
                    Saving…
                  </>
                ) : (
                  <>
                    Continue
                    <ArrowRight className="ml-1.5 h-4 w-4" aria-hidden />
                  </>
                )}
              </button>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
