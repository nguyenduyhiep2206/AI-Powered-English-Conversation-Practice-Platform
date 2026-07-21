"use client";

import Link from "next/link";
import { Check, Lock, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { RoadmapWeek } from "@/lib/roadmap";

const MASTERY_PASS = 0.7;

type WeekNodeProps = {
  week: RoadmapWeek;
  offset: "left" | "right" | "center";
  completing: boolean;
  actionError: string | null;
  onComplete: (week: RoadmapWeek) => void;
  onLockedTap: () => void;
};

export function WeekNode({
  week,
  offset,
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
        "relative flex w-full max-w-md flex-col items-center",
        offset === "left" && "self-start sm:ml-4",
        offset === "right" && "self-end sm:mr-4",
        offset === "center" && "self-center",
      )}
    >
      <button
        type="button"
        onClick={() => {
          if (week.status === "locked") onLockedTap();
        }}
        className={cn(
          "relative flex h-16 w-16 items-center justify-center rounded-full border-2 transition-transform",
          week.status === "completed" &&
            "border-emerald-500/60 bg-emerald-500/20 text-emerald-300",
          week.status === "in_progress" &&
            "border-primary bg-primary text-primary-foreground shadow-[0_0_0_6px_oklch(1_0_0/0.06)] motion-safe:animate-pulse",
          week.status === "locked" &&
            "border-border bg-muted/40 text-muted-foreground",
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

      <div className="mt-3 w-full rounded-xl border border-border/70 bg-card/50 px-4 py-3 text-left backdrop-blur-sm">
        <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
          Week {week.week_number}
        </p>
        <p className="mt-1 text-sm font-medium text-foreground">{title}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">{week.title}</p>

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
                  masteryPct >= 70 ? "bg-emerald-400" : "bg-primary",
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
