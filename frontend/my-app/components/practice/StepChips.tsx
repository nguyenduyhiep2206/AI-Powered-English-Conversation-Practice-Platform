"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export type StepChipId = "learn" | "practice" | "path";
export type StepChipState = "upcoming" | "active" | "done";

export type StepChip = {
  id: StepChipId;
  label: string;
  state: StepChipState;
  detail?: string;
};

export function StepChips({
  steps,
  onSelect,
  selectableIds,
}: {
  steps: StepChip[];
  onSelect?: (id: StepChipId) => void;
  selectableIds?: StepChipId[];
}) {
  const canSelect = (id: StepChipId, state: StepChipState) =>
    Boolean(onSelect && selectableIds?.includes(id) && state !== "active");

  return (
    <nav aria-label="Lesson progress" className="mt-3 flex flex-wrap gap-2">
      {steps.map((step, i) => {
        const interactive = canSelect(step.id, step.state);
        const className = cn(
          "inline-flex min-h-9 items-center gap-1.5 rounded-2xl px-3 text-[0.75rem] font-medium ring-1",
          step.state === "active" &&
            "bg-[#FFE8D6] text-[#9A3412] ring-[#E85D04]/35",
          step.state === "done" &&
            "bg-[#D8F3DC] text-[#2F9E44] ring-[#2F9E44]/35",
          step.state === "upcoming" &&
            "bg-white/80 text-[#6B6258] ring-[#E9D7C9]",
          interactive &&
            "cursor-pointer transition-colors hover:ring-[#E85D04]/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]",
          !interactive && step.state !== "active" && "opacity-80",
        );
        const body = (
          <>
            <span className="tabular-nums text-[#A89F94]">{i + 1}.</span>
            {step.label}
            {step.detail ? ` ${step.detail}` : ""}
            {step.state === "done" ? (
              <Check className="h-3.5 w-3.5" aria-hidden strokeWidth={2.5} />
            ) : null}
          </>
        );
        if (interactive) {
          return (
            <button
              key={step.id}
              type="button"
              className={className}
              onClick={() => onSelect?.(step.id)}
            >
              {body}
            </button>
          );
        }
        return (
          <span
            key={step.id}
            className={className}
            aria-current={step.state === "active" ? "step" : undefined}
          >
            {body}
          </span>
        );
      })}
    </nav>
  );
}
