"use client";

import type { CSSProperties } from "react";
import Link from "next/link";
import { Check, Lock, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { RoadmapWeek } from "@/lib/roadmap";

const MASTERY_PASS = 0.7;

type WeekNodeProps = {
  week: RoadmapWeek;
  offset: "left" | "right" | "center";
  index?: number;
  completing: boolean;
  actionError: string | null;
  onComplete: (week: RoadmapWeek) => void;
  onLockedTap: () => void;
};

export function WeekNode({
  week,
  offset,
  index = 0,
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

  return (
    <div
      className={cn(
        "relative flex w-full flex-col items-center",
        isActive ? "max-w-md" : "max-w-[20rem]",
        offset === "left" && "self-start sm:ml-1",
        offset === "right" && "self-end sm:mr-1",
        offset === "center" && "self-center",
      )}
      style={{ "--ef-index": Math.min(index, 4) } as CSSProperties}
    >
      <button
        type="button"
        onClick={() => {
          if (isLocked) onLockedTap();
        }}
        className={cn(
          "relative z-[1] flex items-center justify-center transition-[transform,box-shadow,background-color] duration-200",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF8A6B] focus-visible:ring-offset-2 focus-visible:ring-offset-[#FFF8F4]",
          "active:scale-[0.96]",
          isActive &&
            "h-[4.5rem] w-[4.5rem] rounded-[1.35rem] bg-[#FF8A6B] text-white shadow-[0_10px_28px_rgba(255,138,107,0.4)] ring-4 ring-[#FF8A6B]/20",
          isDone &&
            "h-14 w-14 rounded-[1.25rem] bg-[#8CC6E8] text-white shadow-[0_6px_16px_rgba(140,198,232,0.35)]",
          isLocked &&
            "h-14 w-14 cursor-pointer rounded-[1.25rem] bg-white text-[#B0A9B8] shadow-[0_4px_14px_rgba(42,36,56,0.06)] ring-1 ring-[#2A2438]/06",
        )}
        aria-label={`${title}. Step ${week.week_number}, ${week.status.replace("_", " ")}`}
      >
        {isDone ? (
          <Check className="h-6 w-6" strokeWidth={2.5} aria-hidden />
        ) : isLocked ? (
          <Lock className="h-5 w-5" aria-hidden />
        ) : (
          <Sparkles className="h-6 w-6" aria-hidden />
        )}
      </button>

      {isDone ? (
        <div className="mt-3 w-full rounded-[1.35rem] bg-white/90 px-4 py-3 text-center ring-1 ring-[#2A2438]/06">
          <p className="text-[0.8125rem] font-semibold leading-snug text-[#2A2438]">
            {title}
          </p>
          <p className="mt-0.5 text-[0.75rem] font-medium text-[#8CC6E8]">
            Done · {masteryPct}%
          </p>
        </div>
      ) : null}

      {isLocked ? (
        <button
          type="button"
          onClick={onLockedTap}
          className="mt-3 w-full rounded-[1.35rem] bg-white/70 px-4 py-3 text-center ring-1 ring-[#2A2438]/05 transition-colors hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF8A6B]/50"
        >
          <p className="text-[0.8125rem] font-medium leading-snug text-[#8A8396]">
            {title}
          </p>
          <p className="mt-0.5 text-[0.75rem] text-[#B0A9B8]">
            Step {week.week_number} · Locked
          </p>
        </button>
      ) : null}

      {isActive ? (
        <div className="mt-4 w-full rounded-[1.75rem] bg-white px-5 py-5 text-left shadow-[0_18px_50px_rgba(42,36,56,0.08)] ring-1 ring-[#FF8A6B]/30">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-xl bg-[#FF8A6B]/12 px-2.5 py-1 text-[0.75rem] font-semibold text-[#C45D42]">
              Current step
            </span>
            <span className="text-[0.75rem] font-medium tabular-nums text-[#8A8396]">
              Step {week.week_number}
              {week.level ? ` · ${week.level}` : ""}
            </span>
          </div>
          <h3 className="mt-2.5 text-lg font-semibold leading-snug tracking-tight text-[#2A2438]">
            {title}
          </h3>
          {week.title && week.title !== title ? (
            <p className="mt-1 text-sm leading-relaxed text-[#6B6478]">
              {week.title}
            </p>
          ) : null}

          <div className="mt-4">
            <div className="mb-1.5 flex items-center justify-between text-[0.8125rem] font-medium">
              <span className="text-[#6B6478]">Mastery</span>
              <span className="tabular-nums text-[#2A2438]">{masteryPct}%</span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-[#FFF0E8]"
              role="progressbar"
              aria-valuenow={masteryPct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Mastery progress"
            >
              <div
                className={cn(
                  "h-full rounded-full transition-[width] duration-300 ease-out",
                  masteryPct >= 70 ? "bg-[#8CC6E8]" : "bg-[#FF8A6B]",
                )}
                style={{ width: `${Math.min(100, masteryPct)}%` }}
              />
            </div>
            <p className="mt-2 text-[0.8125rem] leading-relaxed text-[#6B6478]">
              Reach 70% mastery in Learn → Practice, then complete this week.
            </p>
          </div>

          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <Button
              asChild
              type="button"
              className="h-11 flex-1 rounded-2xl bg-[#FF8A6B] text-[0.875rem] font-semibold text-white shadow-[0_10px_24px_rgba(255,138,107,0.28)] hover:bg-[#F47A5A] active:scale-[0.98]"
            >
              <Link href={`/dashboard/practice/${week.skill_id}`}>
                Continue practice
              </Link>
            </Button>
            <Button
              type="button"
              className="h-11 flex-1 rounded-2xl bg-[#FFF0E8] text-[0.875rem] font-semibold text-[#C45D42] hover:bg-[#FFE4D6] disabled:opacity-45"
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
              className="mt-3 rounded-2xl bg-[#FFF0EE] px-3 py-2 text-[0.8125rem] text-[#C24B3A]"
              role="alert"
            >
              {actionError}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
