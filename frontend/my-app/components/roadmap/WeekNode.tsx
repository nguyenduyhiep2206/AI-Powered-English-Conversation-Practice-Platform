"use client";

import type { CSSProperties } from "react";
import Link from "next/link";
import { Check, Flag, Lock, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { RoadmapWeek } from "@/lib/roadmap";

const MASTERY_PASS = 0.7;

type WeekNodeProps = {
  week: RoadmapWeek;
  index?: number;
  isLast?: boolean;
  isPathEnd?: boolean;
  completing: boolean;
  actionError: string | null;
  onComplete: (week: RoadmapWeek) => void;
  onLockedTap: () => void;
};

export function WeekNode({
  week,
  index = 0,
  isLast = false,
  isPathEnd = false,
  completing,
  actionError,
  onComplete,
  onLockedTap,
}: WeekNodeProps) {
  const masteryPct = Math.round(week.mastery * 100);
  const canComplete =
    week.status === "in_progress" && week.mastery >= MASTERY_PASS;
  const title = week.skill_title || week.skill_slug;
  const isActive = week.status === "in_progress";
  const isDone = week.status === "completed";
  const isLocked = week.status === "locked";
  const showReadyChip = isActive && canComplete;

  return (
    <li
      className="relative grid grid-cols-[2.75rem_minmax(0,1fr)] gap-x-4 motion-safe:animate-[ef-path-in_420ms_cubic-bezier(0.22,1,0.36,1)_both]"
      style={
        {
          animationDelay: `${Math.min(index, 6) * 40}ms`,
        } as CSSProperties
      }
    >
      {/* Lumingo left rail: circle + stem */}
      <div className="relative flex justify-center">
        {!isLast ? (
          <div
            className={cn(
              "absolute top-11 bottom-[-1.25rem] w-[3px] rounded-full",
              isDone ? "bg-[#2F9E44]" : "bg-[#E9D7C9]",
            )}
            aria-hidden
          />
        ) : null}

        {isActive ? (
          <div
            className="pointer-events-none absolute top-1 size-14 rounded-full bg-[#E85D04]/25 blur-md"
            aria-hidden
          />
        ) : null}

        <button
          type="button"
          onClick={() => {
            if (isLocked) onLockedTap();
          }}
          className={cn(
            "relative z-[1] mt-0.5 flex size-11 shrink-0 items-center justify-center rounded-full transition-[transform,box-shadow] duration-200",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04] focus-visible:ring-offset-2 focus-visible:ring-offset-[#FFF5EB]",
            "active:scale-[0.96]",
            isActive &&
              "bg-[#E85D04] text-white shadow-[0_10px_22px_-6px_rgba(232,93,4,0.55)]",
            isDone &&
              "bg-[#2F9E44] text-white shadow-[0_8px_18px_-8px_rgba(47,158,68,0.55)]",
            isLocked &&
              "cursor-pointer border border-[#E9D7C9] bg-[#FFFAF5] text-[#A89F94] shadow-[0_6px_14px_-10px_rgba(31,27,21,0.35)]",
            isPathEnd &&
              isLocked &&
              "border-2 border-[#E85D04] bg-white text-[#E85D04]",
          )}
          aria-label={`${title}. Step ${week.week_number}, ${week.status.replace("_", " ")}`}
        >
          {isDone ? (
            <Check className="h-5 w-5" strokeWidth={2.75} aria-hidden />
          ) : isPathEnd && isLocked ? (
            <Flag className="h-4 w-4" aria-hidden />
          ) : isLocked ? (
            <Lock className="h-4 w-4" aria-hidden />
          ) : (
            <Play className="h-5 w-5 fill-current" aria-hidden />
          )}
        </button>
      </div>

      {/* Right label + optional active sheet */}
      <div className={cn("min-w-0", isLast ? "pb-0" : "pb-8")}>
        <div className="flex flex-wrap items-center gap-2 pt-2">
          {showReadyChip ? (
            <span className="rounded-full bg-[#CCFBF1] px-2.5 py-0.5 text-[0.75rem] font-semibold text-[#115E59]">
              Ready
            </span>
          ) : null}
          <p className="text-base font-medium leading-snug text-[#1F1B15]">
            Step {week.week_number} · {title}
          </p>
        </div>
        <p
          className={cn(
            "mt-0.5 text-[0.8125rem] font-medium tabular-nums",
            isDone && "text-[#2F9E44]",
            isActive && "text-[#9A3412]",
            isLocked && "text-[#8A8178]",
          )}
        >
          {isDone
            ? `Done · ${masteryPct}%`
            : isActive
              ? `Mastery ${masteryPct}%`
              : "Locked"}
        </p>

        {isActive ? (
          <div className="mt-4 rounded-[1.75rem] border border-[#E9D7C9] bg-[#FFFAF5] px-5 py-5 shadow-[0_16px_40px_-28px_rgba(31,27,21,0.45)]">
            {week.title && week.title !== title ? (
              <p className="text-[0.9375rem] leading-relaxed text-[#6B6258]">
                {week.title}
              </p>
            ) : (
              <p className="text-[0.9375rem] leading-relaxed text-[#6B6258]">
                Hit 70% in Learn → Practice, then complete this week.
              </p>
            )}

            <div className="mt-4">
              <div className="mb-1.5 flex items-center justify-between text-[0.8125rem] font-medium">
                <span className="text-[#6B6258]">Mastery</span>
                <span className="tabular-nums font-semibold text-[#1F1B15]">
                  {masteryPct}%
                </span>
              </div>
              <div
                className="h-2 overflow-hidden rounded-full bg-[#FFE8D6]"
                role="progressbar"
                aria-valuenow={masteryPct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Mastery progress"
              >
                <div
                  className={cn(
                    "h-full rounded-full transition-[width] duration-300 ease-out",
                    masteryPct >= 70 ? "bg-[#2F9E44]" : "bg-[#E85D04]",
                  )}
                  style={{ width: `${Math.min(100, masteryPct)}%` }}
                />
              </div>
            </div>

            <div className="mt-5 flex flex-col gap-2 sm:flex-row">
              <Button
                asChild
                type="button"
                className="h-11 flex-1 rounded-2xl bg-[#E85D04] text-[0.875rem] font-semibold text-white shadow-[0_10px_22px_-8px_rgba(232,93,4,0.55)] hover:bg-[#D04F00] active:scale-[0.98]"
              >
                <Link href={`/dashboard/practice/${week.skill_id}`}>
                  Continue practice
                </Link>
              </Button>
              <Button
                type="button"
                className="h-11 flex-1 rounded-2xl border border-[#E9D7C9] bg-white text-[0.875rem] font-semibold text-[#9A3412] hover:bg-[#FFF5EB] disabled:opacity-40"
                disabled={!canComplete || completing}
                onClick={() => onComplete(week)}
              >
                {completing
                  ? "Completing…"
                  : canComplete
                    ? "Complete week"
                    : "Need 70% mastery"}
              </Button>
            </div>

            {actionError ? (
              <p
                className="mt-3 rounded-2xl bg-[#FFE4E6] px-3 py-2 text-[0.8125rem] text-[#BE123C]"
                role="alert"
              >
                {actionError}
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    </li>
  );
}
