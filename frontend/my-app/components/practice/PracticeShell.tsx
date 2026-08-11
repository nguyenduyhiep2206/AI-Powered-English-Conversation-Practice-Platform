"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import {
  StepChips,
  type StepChip,
  type StepChipId,
} from "@/components/practice/StepChips";
import { cn } from "@/lib/utils";

type Props = {
  title: string;
  subtitle?: string;
  /** Mini-unit / pack lesson name shown above the Learn card. */
  lessonTitle?: string | null;
  masteryPct: number | null;
  readyToComplete: boolean;
  steps: StepChip[];
  showSteps?: boolean;
  onStepSelect?: (id: StepChipId) => void;
  selectableStepIds?: StepChipId[];
  phase: "learn" | "practice";
  lesson: ReactNode;
  quiz: ReactNode;
  qa: ReactNode | null;
  loading?: boolean;
  loadingLabel?: string;
  banner?: ReactNode;
};

export function PracticeShell({
  title,
  subtitle = "Learn the skill, then practice until Mastery reaches 70%.",
  lessonTitle,
  masteryPct,
  readyToComplete,
  steps,
  showSteps = true,
  onStepSelect,
  selectableStepIds,
  phase,
  lesson,
  quiz,
  qa,
  loading,
  loadingLabel,
  banner,
}: Props) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#FFF5EB] text-[#1F1B15]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 60% 40% at 10% 0%, rgba(232,93,4,0.14), transparent 55%), radial-gradient(ellipse 50% 35% at 90% 10%, rgba(13,148,136,0.1), transparent 50%)",
        }}
      />
      <div className="relative">
        <AppHeader />
        <main className="mx-auto max-w-6xl px-5 py-8 sm:px-6 lg:px-8">
          <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <Link
                href="/dashboard"
                className="inline-flex min-h-11 items-center gap-1.5 text-[0.875rem] font-medium text-[#9A3412] transition-colors hover:text-[#E85D04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden />
                Back to path
              </Link>
              <h1 className="mt-2 text-[1.75rem] font-semibold tracking-tight text-[#1F1B15]">
                {title}
              </h1>
              <p className="mt-1 text-[0.875rem] leading-relaxed text-[#6B6258]">
                {subtitle}
              </p>
              {showSteps ? (
                <StepChips
                  steps={steps}
                  onSelect={onStepSelect}
                  selectableIds={selectableStepIds}
                />
              ) : null}
            </div>
            {masteryPct != null ? (
              <span
                className={cn(
                  "inline-flex min-h-9 items-center rounded-2xl px-3.5 text-[0.8125rem] font-semibold",
                  readyToComplete
                    ? "bg-[#2F9E44] text-white shadow-[0_8px_20px_-8px_rgba(47,158,68,0.55)]"
                    : "bg-white text-[#6B6258] ring-1 ring-[#E9D7C9]",
                )}
              >
                Mastery {masteryPct}%
              </span>
            ) : null}
          </div>

          {banner}

          {loading ? (
            <div className="flex items-center justify-center gap-2 py-20 text-[0.875rem] text-[#6B6258]">
              <Loader2 className="h-5 w-5 animate-spin text-[#E85D04]" aria-hidden />
              {loadingLabel ?? "Loading…"}
            </div>
          ) : phase === "learn" ? (
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,1fr)] lg:items-start">
              <div className="min-w-0 space-y-3">
                <div className="rounded-[2rem] border border-[#E9D7C9] bg-white/80 p-5 shadow-[0_24px_60px_-40px_rgba(31,27,21,0.45)] sm:p-7">
                  {lessonTitle ? (
                    <h2 className="text-[1.25rem] font-semibold tracking-tight text-[#1F1B15]">
                      {lessonTitle}
                    </h2>
                  ) : null}
                  {lesson}
                </div>
              </div>
              {qa ? <div className="min-w-0 lg:sticky lg:top-4">{qa}</div> : null}
            </div>
          ) : (
            <div className="mx-auto max-w-xl">{quiz}</div>
          )}
        </main>
      </div>
    </div>
  );
}
