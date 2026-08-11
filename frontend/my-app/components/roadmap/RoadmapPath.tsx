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
  const total = sorted.length;

  let globalIndex = 0;

  return (
    <div className="relative mx-auto w-full max-w-xl">
      {/* Lumingo-style path panel */}
      <div className="rounded-[2.5rem] border border-[#E9D7C9] bg-white/75 px-5 py-7 shadow-[0_24px_60px_-40px_rgba(31,27,21,0.45)] backdrop-blur-sm sm:px-8 sm:py-8">
        <div className="mb-6">
          <h2 className="text-lg font-semibold tracking-tight text-[#1F1B15]">
            Your path
          </h2>
          <p className="mt-1 text-[0.875rem] leading-relaxed text-[#6B6258]">
            Clear nodes from foundation to goal. Finish the current step to unlock
            what comes next.
          </p>
        </div>

        <div className="flex flex-col gap-2">
          {groups.map((group) => (
            <section key={group.unitKey}>
              {hasThemeUnits ? (
                <header className="mb-4 ml-14">
                  <h3 className="text-[0.9375rem] font-semibold text-[#1F1B15]">
                    {group.title}
                  </h3>
                  {group.canDo ? (
                    <p className="mt-0.5 text-[0.8125rem] leading-relaxed text-[#6B6258]">
                      {group.canDo}
                    </p>
                  ) : null}
                </header>
              ) : null}

              <ol className="list-none p-0">
                {group.weeks.map((week) => {
                  const index = globalIndex;
                  globalIndex += 1;
                  const isLast = index === total - 1;
                  return (
                    <WeekNode
                      key={week.roadmap_step_id}
                      week={week}
                      index={index}
                      isLast={isLast}
                      isPathEnd={isLast}
                      completing={completingStepId === week.roadmap_step_id}
                      actionError={
                        week.status === "in_progress" ? actionError : null
                      }
                      onComplete={onComplete}
                      onLockedTap={() =>
                        setLockedHint(
                          "Finish the current step first. Later steps may change as you progress.",
                        )
                      }
                    />
                  );
                })}
              </ol>
            </section>
          ))}
        </div>

        {lockedHint ? (
          <p
            className="mt-2 ml-14 max-w-sm rounded-2xl bg-[#FFFAF5] px-4 py-3 text-[0.8125rem] leading-relaxed text-[#6B6258] ring-1 ring-[#E9D7C9]"
            role="status"
          >
            {lockedHint}
          </p>
        ) : null}
      </div>
    </div>
  );
}
