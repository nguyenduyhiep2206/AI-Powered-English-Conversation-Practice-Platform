"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import LogoutButton from "@/components/ui/LogoutButton";
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

const KNOW_ENGLISH_OPTIONS: { value: KnowEnglishChoice; label: string; hint: string }[] = [
  { value: "beginner", label: "I'm just starting out", hint: "We'll place you at A1" },
  { value: "know_some", label: "I know some English", hint: "Pick your level or take a short test" },
];

const LEVEL_FORK_OPTIONS: { value: LevelForkChoice; label: string; hint: string }[] = [
  { value: "self_selected", label: "I know my level", hint: "Choose A1–C1 yourself" },
  { value: "placement", label: "Help me find my level", hint: "Short adaptive placement test" },
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
  const order: WizardStep[] = ["why", "time", "know_english", "level_fork", "pick_cefr"];
  return order.indexOf(step) + 1;
}

function cardClass(selected: boolean): string {
  return `rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
    selected
      ? "border-primary bg-primary/15 text-foreground"
      : "border-border bg-background/40 text-muted-foreground hover:border-primary/40 hover:text-foreground"
  }`;
}

export default function OnboardingSurveyPage() {
  const router = useRouter();
  const [whyQuestion, setWhyQuestion] = useState<SurveyQuestion | null>(null);
  const [timeQuestion, setTimeQuestion] = useState<SurveyQuestion | null>(null);
  const [step, setStep] = useState<WizardStep>("why");
  const [whyAnswer, setWhyAnswer] = useState<string | null>(null);
  const [timeAnswer, setTimeAnswer] = useState<string | null>(null);
  const [knowEnglish, setKnowEnglish] = useState<KnowEnglishChoice | null>(null);
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
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!whyQuestion || !timeQuestion) {
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
          <p className="text-sm text-destructive" role="alert">
            {error ?? "Survey is not configured for Busuu-style onboarding"}
          </p>
        </main>
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
        <div className="mb-6">
          <div
            className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-valuenow={Math.round(progress * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${Math.round(progress * 100)}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Step {stepIndex(step)} of {totalSteps}
          </p>
        </div>

        <section className="ef-card rounded-xl border border-border bg-card/60 p-6">
          {step === "why" ? (
            <>
              <h1 className="text-xl font-semibold tracking-tight">{whyQuestion.prompt}</h1>
              <div className="mt-5 grid gap-2">
                {(whyQuestion.options ?? []).map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => {
                      setWhyAnswer(option.value);
                      setError(null);
                    }}
                    className={cardClass(whyAnswer === option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </>
          ) : null}

          {step === "time" ? (
            <>
              <h1 className="text-xl font-semibold tracking-tight">{timeQuestion.prompt}</h1>
              <div className="mt-5 grid gap-2">
                {(timeQuestion.options ?? []).map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => {
                      setTimeAnswer(option.value);
                      setError(null);
                    }}
                    className={cardClass(timeAnswer === option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </>
          ) : null}

          {step === "know_english" ? (
            <>
              <h1 className="text-xl font-semibold tracking-tight">
                How much English do you know?
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                We&apos;ll use this to place you at the right level.
              </p>
              <div className="mt-5 grid gap-2">
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
                    className={cardClass(knowEnglish === option.value)}
                  >
                    <span className="block font-medium text-foreground">{option.label}</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      {option.hint}
                    </span>
                  </button>
                ))}
              </div>
            </>
          ) : null}

          {step === "level_fork" ? (
            <>
              <h1 className="text-xl font-semibold tracking-tight">
                How should we set your level?
              </h1>
              <div className="mt-5 grid gap-2">
                {LEVEL_FORK_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => {
                      setLevelFork(option.value);
                      setCefrLevel(null);
                      setError(null);
                    }}
                    className={cardClass(levelFork === option.value)}
                  >
                    <span className="block font-medium text-foreground">{option.label}</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      {option.hint}
                    </span>
                  </button>
                ))}
              </div>
            </>
          ) : null}

          {step === "pick_cefr" ? (
            <>
              <h1 className="text-xl font-semibold tracking-tight">
                Which level fits you best?
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Pick the CEFR level that matches your current ability.
              </p>
              <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3">
                {CEFR_LEVELS.map((level) => (
                  <button
                    key={level}
                    type="button"
                    onClick={() => {
                      setCefrLevel(level);
                      setError(null);
                    }}
                    className={cardClass(cefrLevel === level)}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </>
          ) : null}

          {error ? (
            <p className="mt-4 text-sm text-destructive" role="alert">
              {error}
            </p>
          ) : null}

          <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
            {step !== "why" ? (
              <Button type="button" variant="ghost" onClick={handleBack} disabled={submitting}>
                Back
              </Button>
            ) : (
              <Button type="button" variant="ghost" asChild>
                <Link href="/start-onboarding">Back</Link>
              </Button>
            )}
            <Button
              type="button"
              size="lg"
              disabled={submitting || !canContinue}
              onClick={handleContinue}
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving…
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
      </main>
    </div>
  );
}
