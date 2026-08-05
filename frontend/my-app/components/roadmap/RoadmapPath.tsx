"use client";

import { useMemo, useState } from "react";
import { WeekNode } from "@/components/roadmap/WeekNode";
import { groupWeeksByThemeUnit, type RoadmapWeek } from "@/lib/roadmap";

type RoadmapPathProps = {
  weeks: RoadmapWeek[];
  completingStepId: number | null;
  actionError: string | null;
  onComplete: (week: RoadmapWeek) => void;
};

export function RoadmapPath({
  weeks,
  completingStepId,
  actionError,
  onComplete,
}: RoadmapPathProps) {
  const [lockedHint, setLockedHint] = useState<string | null>(null);

  const sorted = useMemo(
    () => [...weeks].sort((a, b) => a.week_number - b.week_number),
    [weeks],
  );
  const groups = useMemo(() => groupWeeksByThemeUnit(sorted), [sorted]);
  const hasThemeUnits = groups.some((g) => !g.unitKey.startsWith("_skill_"));

  let globalIndex = 0;

  return (
    <div className="relative mx-auto flex w-full max-w-lg flex-col items-stretch gap-10 py-2">
      <div
        className="pointer-events-none absolute top-8 bottom-8 left-1/2 w-px -translate-x-1/2 bg-border/80"
        aria-hidden
      />

      {groups.map((group) => (
        <section key={group.unitKey} className="relative z-10 space-y-6">
          {hasThemeUnits ? (
            <header className="px-2 text-center">
              <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                Unit
              </p>
              <h2 className="mt-1 text-lg font-semibold tracking-tight text-foreground">
                {group.title}
              </h2>
              {group.canDo ? (
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                  {group.canDo}
                </p>
              ) : null}
            </header>
          ) : null}

          {group.weeks.map((week) => {
            const index = globalIndex;
            globalIndex += 1;
            const offset =
              week.status === "in_progress"
                ? "center"
                : index % 2 === 0
                  ? "left"
                  : "right";
            return (
              <WeekNode
                key={week.roadmap_step_id}
                week={week}
                offset={offset}
                index={index}
                completing={completingStepId === week.roadmap_step_id}
                actionError={
                  week.status === "in_progress" ? actionError : null
                }
                onComplete={onComplete}
                onLockedTap={() =>
                  setLockedHint(
                    "Finish the current step first — future steps may change as you progress.",
                  )
                }
              />
            );
          })}
        </section>
      ))}

      {lockedHint ? (
        <p className="text-center text-xs text-muted-foreground" role="status">
          {lockedHint}
        </p>
      ) : null}
    </div>
  );
}
