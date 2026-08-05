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

export function StepChips({ steps }: { steps: StepChip[] }) {
  return (
    <nav aria-label="Lesson progress" className="mt-3 flex flex-wrap gap-2">
      {steps.map((step, i) => (
        <span
          key={step.id}
          className={cn(
            "inline-flex min-h-9 items-center gap-1.5 rounded-2xl px-3 text-[0.75rem] font-medium ring-1",
            step.state === "active" &&
              "bg-[#FFF0E8] text-[#C45D42] ring-[#FF8A6B]/35",
            step.state === "done" &&
              "bg-[#E8F4FB] text-[#3D7FA0] ring-[#8CC6E8]/40",
            step.state === "upcoming" &&
              "bg-white/70 text-[#8A8396] ring-[#2A2438]/06",
          )}
        >
          <span className="tabular-nums text-[#B0A9B8]">{i + 1}.</span>
          {step.label}
          {step.detail ? ` ${step.detail}` : ""}
          {step.state === "done" ? (
            <Check className="h-3.5 w-3.5" aria-hidden strokeWidth={2.5} />
          ) : null}
        </span>
      ))}
    </nav>
  );
}
