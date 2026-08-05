"use client";

import { Badge } from "@/components/ui/badge";
import type { TutorScenario } from "@/lib/tutor";

type TutorScenarioRailProps = {
  scenario: TutorScenario;
  status?: string;
};

export default function TutorScenarioRail({
  scenario,
  status,
}: TutorScenarioRailProps) {
  const vocab = scenario.suggested_vocab?.filter(Boolean) ?? [];

  return (
    <aside className="hidden w-72 shrink-0 flex-col border-r border-border/60 bg-muted/20 lg:flex">
      <div className="flex-1 overflow-y-auto px-4 py-5">
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Scenario
        </p>
        <h2 className="mt-2 text-base font-semibold leading-snug tracking-tight text-foreground">
          {scenario.title}
        </h2>

        <div className="mt-3 flex flex-wrap gap-1.5">
          <Badge variant="secondary" className="capitalize">
            {scenario.category}
          </Badge>
          <Badge variant="outline" className="uppercase">
            {scenario.level}
          </Badge>
          {status ? (
            <Badge variant="outline" className="capitalize">
              {status}
            </Badge>
          ) : null}
        </div>

        <dl className="mt-6 space-y-4 text-sm">
          <div>
            <dt className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
              Your role
            </dt>
            <dd className="mt-1 leading-relaxed text-foreground">
              {scenario.user_role}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
              AI partner
            </dt>
            <dd className="mt-1 leading-relaxed text-foreground">
              {scenario.ai_role}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
              Goal
            </dt>
            <dd className="mt-1 leading-relaxed text-foreground">
              {scenario.goal_prompt}
            </dd>
          </div>
        </dl>

        {vocab.length > 0 ? (
          <div className="mt-6">
            <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
              Suggested vocab
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {vocab.map((word) => (
                <span
                  key={word}
                  className="rounded-md border border-border/70 bg-background px-2 py-0.5 text-xs text-foreground"
                >
                  {word}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
