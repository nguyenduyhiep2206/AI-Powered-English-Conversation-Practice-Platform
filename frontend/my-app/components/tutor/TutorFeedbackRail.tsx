"use client";

import { Lightbulb, PanelRightClose, PanelRightOpen } from "lucide-react";
import type { TutorFeedbackItem } from "@/lib/tutor-feedback";
import { cn } from "@/lib/utils";

type TutorFeedbackRailProps = {
  items: TutorFeedbackItem[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

function FeedbackCard({ item }: { item: TutorFeedbackItem }) {
  if (item.kind === "hint") {
    return (
      <article className="rounded-2xl bg-[#CCFBF1]/60 px-3.5 py-3 ring-1 ring-[#0D9488]/20">
        <div className="flex items-center gap-1.5">
          <Lightbulb className="h-3.5 w-3.5 text-[#0D9488]" aria-hidden />
          <span className="text-[0.75rem] font-semibold text-[#115E59]">
            Hint
          </span>
        </div>
        <p className="mt-2 text-[0.875rem] leading-relaxed text-[#1F1B15]">
          {item.note}
        </p>
      </article>
    );
  }

  return (
    <article className="rounded-2xl bg-[#FFE8D6]/70 px-3.5 py-3 ring-1 ring-[#E85D04]/20">
      <span className="text-[0.75rem] font-semibold text-[#9A3412]">
        Correction
      </span>
      {item.original ? (
        <p className="mt-2 text-[0.875rem] text-[#8A8178] line-through">
          {item.original}
        </p>
      ) : null}
      {item.corrected ? (
        <p className="mt-1 text-[0.875rem] font-medium leading-relaxed text-[#1F1B15]">
          {item.corrected}
        </p>
      ) : null}
      {item.note ? (
        <p className="mt-1.5 text-[0.8125rem] leading-relaxed text-[#6B6258]">
          {item.note}
        </p>
      ) : null}
    </article>
  );
}

export default function TutorFeedbackRail({
  items,
  open,
  onOpenChange,
}: TutorFeedbackRailProps) {
  if (!open) {
    return (
      <div className="pointer-events-none fixed bottom-20 right-4 z-40 sm:bottom-6">
        <button
          type="button"
          className="pointer-events-auto inline-flex min-h-11 items-center rounded-2xl bg-white px-4 text-[0.875rem] font-semibold text-[#9A3412] shadow-[0_10px_28px_rgba(31,27,21,0.12)] ring-1 ring-[#E9D7C9] transition-colors hover:bg-[#FFFAF5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
          onClick={() => onOpenChange(true)}
        >
          <PanelRightOpen className="mr-1.5 h-4 w-4" aria-hidden />
          Show feedback
          {items.length > 0 ? (
            <span className="ml-2 rounded-xl bg-[#FFE8D6] px-2 py-0.5 text-[0.75rem] font-semibold tabular-nums text-[#9A3412]">
              {items.length}
            </span>
          ) : null}
        </button>
      </div>
    );
  }

  return (
    <aside
      className={cn(
        "fixed inset-y-0 right-0 z-40 flex w-[min(100vw,20rem)] flex-col border-l border-[#E9D7C9] bg-white shadow-[0_24px_60px_rgba(31,27,21,0.14)]",
        "lg:static lg:z-0 lg:w-72 lg:shrink-0 lg:bg-[#FFFAF5]/80 lg:shadow-none",
      )}
    >
      <div className="flex items-center justify-between border-b border-[#E9D7C9] px-4 py-3.5">
        <p className="text-[0.9375rem] font-semibold text-[#1F1B15]">
          Feedback
        </p>
        <button
          type="button"
          aria-label="Hide feedback"
          onClick={() => onOpenChange(false)}
          className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-[#6B6258] transition-colors hover:bg-[#FFF5EB] hover:text-[#1F1B15] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D04]"
        >
          <PanelRightClose className="h-4 w-4" aria-hidden />
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {items.length === 0 ? (
          <p className="text-[0.875rem] leading-relaxed text-[#8A8178]">
            Corrections and hints from this session will show up here.
          </p>
        ) : (
          items.map((item) => <FeedbackCard key={item.id} item={item} />)
        )}
      </div>
    </aside>
  );
}
