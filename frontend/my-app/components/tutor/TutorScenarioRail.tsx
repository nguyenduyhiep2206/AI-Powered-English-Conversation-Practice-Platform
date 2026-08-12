"use client";

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
    <aside className="hidden w-72 shrink-0 flex-col border-r border-[#E9D7C9] bg-[#FFFAF5]/80 lg:flex">
      <div className="flex-1 overflow-y-auto px-5 py-5">
        <h2 className="text-[1.25rem] font-semibold leading-snug tracking-tight text-[#1F1B15]">
          {scenario.title}
        </h2>
        <p className="mt-1 text-[0.8125rem] text-[#8A8178]">Scenario brief</p>

        <div className="mt-4 flex flex-wrap gap-1.5">
          <span className="rounded-2xl bg-[#CCFBF1] px-2.5 py-1 text-[0.75rem] font-semibold capitalize text-[#115E59]">
            {scenario.category}
          </span>
          <span className="rounded-2xl bg-[#FFE8D6] px-2.5 py-1 text-[0.75rem] font-semibold text-[#9A3412]">
            {scenario.level}
          </span>
          {status ? (
            <span className="rounded-2xl bg-white px-2.5 py-1 text-[0.75rem] font-medium capitalize text-[#6B6258] ring-1 ring-[#E9D7C9]">
              {status}
            </span>
          ) : null}
        </div>

        <dl className="mt-6 space-y-5 text-[0.9375rem]">
          <div>
            <dt className="text-[0.8125rem] font-medium text-[#8A8178]">
              Your role
            </dt>
            <dd className="mt-1 leading-relaxed text-[#1F1B15]">
              {scenario.user_role}
            </dd>
          </div>
          <div>
            <dt className="text-[0.8125rem] font-medium text-[#8A8178]">
              AI partner
            </dt>
            <dd className="mt-1 leading-relaxed text-[#1F1B15]">
              {scenario.ai_role}
            </dd>
          </div>
          <div>
            <dt className="text-[0.8125rem] font-medium text-[#8A8178]">
              Goal
            </dt>
            <dd className="mt-1 leading-relaxed text-[#1F1B15]">
              {scenario.goal_prompt}
            </dd>
          </div>
        </dl>

        {vocab.length > 0 ? (
          <div className="mt-6">
            <p className="text-[0.8125rem] font-medium text-[#8A8178]">
              Suggested vocab
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {vocab.map((word) => (
                <span
                  key={word}
                  className="rounded-xl bg-white px-2.5 py-1 text-[0.75rem] font-medium text-[#1F1B15] ring-1 ring-[#E9D7C9]"
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
