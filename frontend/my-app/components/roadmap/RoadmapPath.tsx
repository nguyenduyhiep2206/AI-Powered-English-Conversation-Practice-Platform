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
    <div className="relative mx-auto flex w-full max-w-lg flex-col items-stretch gap-10 py-1">
      <div
        className="pointer-events-none absolute top-8 bottom-8 left-1/2 w-[3px] -translate-x-1/2 rounded-full bg-gradient-to-b from-[#FF8A6B]/50 via-[#8CC6E8]/40 to-[#C4B0E8]/45"
        aria-hidden
      />

      {groups.map((group) => (
        <section key={group.unitKey} className="relative z-10 space-y-6">
          {hasThemeUnits ? (
            <header className="relative flex flex-col items-center px-3 text-center">
              <div className="rounded-2xl bg-white/90 px-4 py-2.5 shadow-[0_4px_14px_rgba(42,36,56,0.05)] ring-1 ring-[#2A2438]/06">
                <h2 className="text-[0.9375rem] font-semibold tracking-tight text-[#2A2438]">
                  {group.title}
                </h2>
                {group.canDo ? (
                  <p className="mt-1 max-w-xs text-[0.8125rem] leading-relaxed text-[#6B6478]">
                    {group.canDo}
                  </p>
                ) : null}
              </div>
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
                    "Finish the current step first — later steps may change as you progress.",
                  )
                }
              />
            );
          })}
        </section>
      ))}

      {lockedHint ? (
        <p
          className="relative z-10 mx-auto max-w-sm rounded-2xl bg-white px-4 py-2.5 text-center text-[0.8125rem] leading-relaxed text-[#6B6478] shadow-[0_4px_14px_rgba(42,36,56,0.05)] ring-1 ring-[#2A2438]/06"
          role="status"
        >
          {lockedHint}
        </p>
      ) : null}
    </div>
  );
}
