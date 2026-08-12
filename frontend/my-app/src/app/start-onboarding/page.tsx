"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  ClipboardList,
  Clock3,
  Loader2,
  PencilLine,
  Route as RouteIcon,
  Target,
} from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { cn } from "@/lib/utils";
import {
  fetchOnboardingStatus,
  type OnboardingStep,
} from "@/lib/onboarding-status";

const STEPS = [
  {
    icon: ClipboardList,
    title: "Quick survey",
    desc: "Why you learn, daily study time, and how we place your level",
    tone: "bg-[#FFE8D6] text-[#E85D04]",
  },
  {
    icon: PencilLine,
    title: "Placement test",
    desc: "Optional — only if you want help finding your CEFR level",
    tone: "bg-[#CCFBF1] text-[#0D9488]",
  },
  {
    icon: Target,
    title: "Personalized plan",
    desc: "Get your CEFR level (A1–C1) and a roadmap built around it",
    tone: "bg-[#D8F3DC] text-[#2F9E44]",
  },
] as const;

const LEVELS = ["A1", "A2", "B1", "B2", "C1"] as const;

export default function StartOnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<OnboardingStep>("survey");
  const [ready, setReady] = useState(false);
  const [navigating, setNavigating] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetchOnboardingStatus()
      .then((data) => {
        if (data.onboarding_complete) {
          router.replace("/dashboard");
          return;
        }
        setCurrentStep(data.current_step);
        setReady(true);
      })
      .catch((err) => {
        console.error("Failed to load onboarding status:", err);
        setLoadError(
          err instanceof Error ? err.message : "Could not load setup status",
        );
        setReady(true);
      });
  }, [router]);

  const isContinue = currentStep === "placement";

  function handleContinue() {
    if (navigating) return;
    setNavigating(true);
    router.push(isContinue ? "/onboarding/placement" : "/onboarding");
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#FFF5EB] text-[#1F1B15]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 60% 45% at 12% 10%, rgba(232, 93, 4, 0.16), transparent 58%), radial-gradient(ellipse 50% 40% at 88% 72%, rgba(13, 148, 136, 0.12), transparent 55%), radial-gradient(ellipse 35% 30% at 70% 8%, rgba(47, 158, 68, 0.08), transparent 50%)",
        }}
      />

      <div className="relative flex min-h-screen flex-col">
        <AppHeader />

        <main className="mx-auto flex w-full max-w-3xl flex-1 items-center px-5 py-10 sm:px-8 md:py-12">
          {!ready ? (
            <div className="flex w-full items-center justify-center gap-2 py-20 text-[0.875rem] text-[#8A8178]">
              <Loader2
                className="h-5 w-5 animate-spin text-[#E85D04]"
                aria-hidden
              />
              Preparing your setup…
            </div>
          ) : (
            <div
              className="ef-fade-up w-full overflow-hidden rounded-[1.75rem] bg-white shadow-[0_18px_50px_rgba(31,27,21,0.08)] ring-1 ring-[#1F1B15]/06"
              style={{ ["--ef-index" as string]: 0 }}
            >
              <div className="relative border-b border-[#E9D7C9] px-6 py-10 text-center sm:px-10 md:py-12">
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0"
                  style={{
                    background:
                      "radial-gradient(ellipse 70% 70% at 50% 0%, rgba(232, 93, 4, 0.12), transparent 60%)",
                  }}
                />
                <div className="relative flex flex-col items-center">
                  <div className="grid h-14 w-14 place-items-center rounded-2xl bg-[#E85D04] text-white shadow-[0_10px_28px_rgba(232,93,4,0.28)]">
                    <RouteIcon className="h-7 w-7" aria-hidden />
                  </div>

                  <span className="mt-5 inline-flex items-center gap-1.5 rounded-2xl bg-[#CCFBF1] px-3 py-1.5 text-[0.75rem] font-semibold text-[#115E59]">
                    <Clock3 className="h-3.5 w-3.5" aria-hidden />
                    Survey ~2 min
                  </span>

                  <h1 className="mt-4 max-w-xl text-[1.75rem] font-semibold tracking-tight text-[#1F1B15] md:text-[2rem]">
                    {isContinue
                      ? "Continue your setup"
                      : "Build your personalized English plan"}
                  </h1>
                  <p className="mt-3 max-w-lg text-[0.9375rem] leading-relaxed text-[#6B6258]">
                    {isContinue
                      ? "Pick up right where you left off — we saved your progress."
                      : "A short survey first. A placement test only if you ask us to find your level."}
                  </p>
                </div>
              </div>

              {loadError ? (
                <div
                  className="mx-6 mt-6 rounded-2xl bg-[#FFE4E6] px-4 py-3 text-[0.875rem] text-[#BE123C] ring-1 ring-[#BE123C]/25 md:mx-10"
                  role="alert"
                >
                  {loadError}. You can still start setup.
                </div>
              ) : null}

              <ol className="space-y-0 px-6 py-8 md:px-10">
                {STEPS.map((step, index) => {
                  const Icon = step.icon;
                  const isLast = index === STEPS.length - 1;
                  return (
                    <li key={step.title} className="relative flex gap-4">
                      <div className="flex w-11 shrink-0 flex-col items-center">
                        <span
                          className={cn(
                            "relative z-[1] grid size-11 place-items-center rounded-full",
                            step.tone,
                          )}
                        >
                          <Icon className="h-5 w-5" aria-hidden />
                        </span>
                        {!isLast ? (
                          <span
                            aria-hidden
                            className="mt-1 w-0.5 flex-1 min-h-6 rounded-full bg-[#E9D7C9]"
                          />
                        ) : null}
                      </div>
                      <div className={cn("min-w-0 pb-6", isLast && "pb-0")}>
                        <p className="text-[0.8125rem] font-medium text-[#8A8178]">
                          Step {index + 1}
                        </p>
                        <h2 className="mt-0.5 text-[1.25rem] font-semibold tracking-tight text-[#1F1B15]">
                          {step.title}
                        </h2>
                        <p className="mt-1 text-[0.875rem] leading-relaxed text-[#6B6258]">
                          {step.desc}
                        </p>
                      </div>
                    </li>
                  );
                })}
              </ol>

              <div className="mx-6 mb-8 rounded-2xl bg-[#FFFAF5] px-5 py-4 ring-1 ring-[#E9D7C9] md:mx-10">
                <p className="text-[0.875rem] font-medium text-[#6B6258]">
                  Your result maps to a CEFR level
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {LEVELS.map((lvl) => (
                    <span
                      key={lvl}
                      className="rounded-2xl bg-white px-3 py-1 text-[0.8125rem] font-semibold text-[#9A3412] ring-1 ring-[#E9D7C9]"
                    >
                      {lvl}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex justify-center border-t border-[#E9D7C9] px-6 py-6 md:px-10">
                <button
                  type="button"
                  disabled={navigating}
                  aria-busy={navigating}
                  onClick={handleContinue}
                  className="inline-flex h-11 w-full items-center justify-center rounded-2xl bg-[#E85D04] px-6 text-[0.9375rem] font-semibold text-white shadow-[0_10px_24px_rgba(232,93,4,0.28)] transition-[transform,background-color,box-shadow] duration-200 hover:bg-[#D04F00] hover:shadow-[0_12px_28px_rgba(232,93,4,0.34)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] active:scale-[0.98] disabled:opacity-60 md:w-auto"
                >
                  {navigating ? (
                    <>
                      <Loader2
                        className="mr-2 h-4 w-4 animate-spin"
                        aria-hidden
                      />
                      {isContinue ? "Opening placement…" : "Starting…"}
                    </>
                  ) : (
                    <>
                      {isContinue
                        ? "Continue placement test"
                        : "Start onboarding"}
                      <ArrowRight className="ml-1.5 h-4 w-4" aria-hidden />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
