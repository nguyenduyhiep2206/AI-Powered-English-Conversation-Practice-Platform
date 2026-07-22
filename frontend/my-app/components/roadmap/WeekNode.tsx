"use client";

import type { CSSProperties } from "react";
import Link from "next/link";
import { Check, Lock, Zap } from "lucide-react";
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

  return (
    <div
      className={cn(
        "ef-fade-up relative flex w-full max-w-md flex-col items-center",
        offset === "left" && "self-start sm:ml-4",
        offset === "right" && "self-end sm:mr-4",
        offset === "center" && "self-center",
      )}
      style={{ "--ef-index": index } as CSSProperties}
    >
      <button
        type="button"
        onClick={() => {
          if (week.status === "locked") onLockedTap();
        }}
        className={cn(
          "relative flex h-16 w-16 items-center justify-center rounded-full border transition-transform active:scale-95",
          week.status === "completed" &&
            "border-[#346538]/30 bg-[#EDF3EC] text-[#346538]",
          week.status === "in_progress" &&
            "border-primary bg-primary text-primary-foreground ring-4 ring-primary/10",
          week.status === "locked" &&
            "cursor-pointer border-border bg-muted/30 text-muted-foreground",
        )}
        aria-label={`${week.title} — ${week.status}`}
      >
        {week.status === "completed" ? (
          <Check className="h-7 w-7" />
        ) : week.status === "locked" ? (
          <Lock className="h-6 w-6" />
        ) : (
          <Zap className="h-7 w-7" />
        )}
      </button>

      <div
        className={cn(
          "mt-4 w-full rounded-xl border bg-card px-5 py-4 text-left transition-colors",
          week.status === "in_progress"
            ? "border-primary/40"
            : "border-border/60",
        )}
      >
        <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
          Week {week.week_number}
        </p>
        <p className="mt-1.5 text-sm font-medium leading-tight text-foreground">
          {title}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">{week.title}</p>

        {week.status !== "locked" ? (
          <div className="mt-3">
            <div className="mb-1 flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Mastery</span>
              <span>{masteryPct}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  masteryPct >= 70 ? "bg-[#346538]" : "bg-primary",
                )}
                style={{ width: `${Math.min(100, masteryPct)}%` }}
              />
            </div>
          </div>
        ) : null}

        {week.status === "in_progress" ? (
          <div className="mt-3 space-y-2">
            <p className="text-xs text-muted-foreground">
              Practice this skill until mastery ≥ 70%, then complete the week.
            </p>
            <Button
              asChild
              type="button"
              size="sm"
              variant="secondary"
              className="w-full"
            >
              <Link href={`/dashboard/practice/${week.skill_id}`}>
                Practice skill
              </Link>
            </Button>
            <Button
              type="button"
              size="sm"
              className="w-full"
              disabled={!canComplete || completing}
              onClick={() => onComplete(week)}
            >
              {completing ? "Completing…" : "Complete week"}
            </Button>
            {actionError ? (
              <p className="text-xs text-destructive" role="alert">
                {actionError}
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
