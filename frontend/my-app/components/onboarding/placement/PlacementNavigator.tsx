"use client";

import { useEffect, useRef } from "react";
import { Flag } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ReadingPage } from "./helpers";

type PlacementNavigatorProps = {
  pages: ReadingPage[];
  answers: Record<number, string>;
  markedIds: Set<number>;
  activeItemId: number | null;
  onSelect: (itemId: number) => void;
};

export default function PlacementNavigator({
  pages,
  answers,
  markedIds,
  activeItemId,
  onSelect,
}: PlacementNavigatorProps) {
  const flat = pages.flatMap((p) => p.items);
  const readingIds = new Set(flat.map((item) => item.id));
  const answeredCount = Object.entries(answers).filter(
    ([id, value]) => readingIds.has(Number(id)) && Boolean(value),
  ).length;
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeItemId == null) return;
    const root = scrollRef.current;
    if (!root) return;
    const btn = root.querySelector<HTMLElement>(
      `[data-nav-item="${activeItemId}"]`,
    );
    if (!btn) return;
    btn.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [activeItemId, pages]);

  return (
    <aside className="sticky top-4 z-20 flex h-[calc(100vh-2rem)] max-h-[48rem] flex-col self-start rounded-[1rem] bg-white p-2 shadow-[0_12px_36px_rgba(31,27,21,0.06)] ring-1 ring-[#1F1B15]/06">
      <div className="flex shrink-0 items-center justify-between gap-2">
        <p className="text-[0.875rem] font-semibold text-[#1F1B15]">
          Questions
        </p>
        <p className="text-[0.75rem] font-medium text-[#8A8178]">
          {answeredCount}/{flat.length}
        </p>
      </div>

      <div className="mt-3 flex shrink-0 flex-wrap gap-x-3 gap-y-1.5 text-[0.75rem] text-[#8A8178]">
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm bg-[#FFE8D6] ring-1 ring-[#E85D04]/40" />{" "}
          Answered
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm bg-[#E9D7C9]" /> Unanswered
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Flag className="h-3 w-3 text-[#0D9488]" aria-hidden /> Marked
        </span>
      </div>

      <div
        ref={scrollRef}
        className="mt-4 grid min-h-0 flex-1 grid-cols-5 content-start gap-1.5 overflow-y-auto p-1 sm:grid-cols-8 lg:grid-cols-5"
      >
        {flat.map((item) => {
          const answered = Boolean(answers[item.id]);
          const marked = markedIds.has(item.id);
          const active = activeItemId === item.id;
          return (
            <button
              key={item.id}
              type="button"
              data-nav-item={item.id}
              onClick={() => onSelect(item.id)}
              aria-label={`Question ${item.globalIndex}${answered ? ", answered" : ", unanswered"}${marked ? ", marked for review" : ""}`}
              aria-current={active ? "true" : undefined}
              className={cn(
                "relative inline-flex h-9 items-center justify-center rounded-[1rem] text-[0.75rem] font-semibold tabular-nums transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#E85D04]",
                answered
                  ? "bg-[#FFE8D6] text-[#9A3412]"
                  : "bg-[#FFFAF5] text-[#8A8178] ring-1 ring-inset ring-[#E9D7C9]",
                active && "ring-2 ring-inset ring-[#E85D04]",
              )}
            >
              {item.globalIndex}
              {marked ? (
                <span className="absolute right-0.5 top-0.5 size-2 rounded-full bg-[#0D9488]" />
              ) : null}
            </button>
          );
        })}
      </div>
    </aside>
  );
}
