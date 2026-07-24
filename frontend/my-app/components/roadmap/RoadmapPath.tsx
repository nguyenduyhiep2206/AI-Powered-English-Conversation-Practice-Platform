"use client";

import { useMemo, useState } from "react";
import { WeekNode } from "@/components/roadmap/WeekNode";
import type { RoadmapWeek } from "@/lib/roadmap";

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

  return (
    <div className="relative mx-auto flex w-full max-w-lg flex-col items-stretch gap-8 py-2">
      <div
        className="pointer-events-none absolute top-8 bottom-8 left-1/2 w-px -translate-x-1/2 bg-border/80"
        aria-hidden
      />

      {sorted.map((week, index) => {
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

      {lockedHint ? (
        <p className="text-center text-xs text-muted-foreground" role="status">
          {lockedHint}
        </p>
      ) : null}
    </div>
  );
}
