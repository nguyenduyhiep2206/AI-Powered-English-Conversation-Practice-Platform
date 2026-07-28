"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  ClipboardList,
  PencilLine,
  Target,
  Clock,
  Sparkles,
  Route as RouteIcon,
  ListChecks,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import LogoutButton from "@/components/ui/LogoutButton";
import { fetchOnboardingStatus, type OnboardingStep } from "@/lib/onboarding-status";

export default function StartOnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<OnboardingStep>("survey");
  const [ready, setReady] = useState(false);
  const [navigating, setNavigating] = useState(false);

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
        setReady(true);
      });
  }, [router]);

  if (!ready) return null;

  const isContinue = currentStep === "placement";

  function handleContinue() {
    if (navigating) return;
    setNavigating(true);
    router.push(isContinue ? "/onboarding/placement" : "/onboarding");
  }

  // Survey preferences + adaptive placement (6–15 questions) → level + roadmap
  const steps = [
    {
      icon: ClipboardList,
      title: "Quick Survey",
      desc: "Occupation, learning goal, self-rated weak point & daily study time",
    },
    {
      icon: PencilLine,
      title: "Placement Test",
      desc: "Adaptive 6–15 questions — we adjust difficulty as you answer",
    },
    {
      icon: Target,
      title: "Personalized Plan",
      desc: "Get your CEFR level (A1–C1) and a roadmap built around it",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex items-center justify-between px-6 py-4">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-white">
              <Sparkles className="h-4 w-4 text-black" />
            </div>
            <span className="font-semibold tracking-tight text-foreground">EnglishFlow</span>
          </Link>
          <div className="flex items-center gap-0.5 rounded-lg border border-border/60 bg-card/40 p-1 backdrop-blur-sm">
            <div className="mx-0.5 h-4 w-px bg-border/70" aria-hidden />
            <LogoutButton />
          </div>
        </div>
      </header>

      <main className="mx-auto flex min-h-[calc(100vh-73px)] max-w-3xl items-center px-6 py-12">
        <div className="w-full overflow-hidden rounded-xl border border-border bg-card">
          <div className="flex flex-col items-center gap-4 border-b border-border bg-card px-8 py-10 text-center md:px-12 md:py-12">
            <div className="flex h-16 w-16 items-center justify-center rounded-xl border border-border bg-secondary">
              <RouteIcon className="h-8 w-8 text-foreground" strokeWidth={2} />
            </div>
            <Badge variant="outline" className="gap-1.5">
              <Clock className="h-3 w-3" />
              ~5–7 min
            </Badge>
            <h1 className="max-w-xl text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
              {isContinue ? "Continue your setup" : "Let's build your personalized English plan!"}
            </h1>
            <p className="max-w-lg text-sm text-muted-foreground md:text-base">
              {isContinue
                ? "Pick up right where you left off — we saved your progress."
                : "A quick survey, then a short placement test — so we can place you at the right CEFR level and generate your roadmap."}
            </p>
          </div>

          <div className="grid gap-3 px-6 py-8 md:grid-cols-3 md:px-10">
            {steps.map((s, i) => (
              <div
                key={s.title}
                className="ef-card-hover flex flex-col gap-3 rounded-xl border border-border bg-card/60 p-5"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-primary/30 bg-primary/15 text-primary">
                    <s.icon className="h-5 w-5" />
                  </div>
                  <span className="text-xs font-medium text-muted-foreground">Step {i + 1}</span>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">{s.title}</h3>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* CEFR level preview — reflects the placement test scoring table in the spec (§2.3) */}
          <div className="mx-6 mb-8 flex flex-wrap items-center gap-2 rounded-xl border border-dashed border-border/80 bg-muted/50 px-5 py-4 md:mx-10">
            <ListChecks className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">Your result maps to a CEFR level:</span>
            <div className="flex flex-wrap gap-1.5">
              {["A1", "A2", "B1", "B2", "C1"].map((lvl) => (
                <Badge
                  key={lvl}
                  variant="outline"
                  className="border-border/90 px-2 py-0.5 text-[11px] font-medium text-foreground"
                >
                  {lvl}
                </Badge>
              ))}
            </div>
          </div>

          <div className="flex flex-col-reverse justify-center items-center gap-3 border-t border-border px-6 py-6 md:flex-row md:px-10">
            <Button
              size="lg"
              className="w-full md:w-auto"
              disabled={navigating}
              aria-busy={navigating}
              onClick={handleContinue}
            >
              {navigating
                ? isContinue
                  ? "Opening placement…"
                  : "Starting…"
                : isContinue
                  ? "Continue Placement Test"
                  : "Start Onboarding"}
              {!navigating ? <ArrowRight className="ml-1.5 h-4 w-4" /> : null}
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}